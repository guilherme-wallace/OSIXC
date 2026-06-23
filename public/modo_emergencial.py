import csv
import json
import os
from datetime import datetime
from uuid import uuid4

from public.ixc_client import IXCAPIError, fechar_os, listar_os, obter_os_por_id
from public.travas_seguranca import autorizar_fechamento


CAMPOS_REVISAO = [
    "id",
    "id_ticket",
    "id_cliente",
    "setor",
    "status",
    "data_abertura",
    "mensagem",
    "inconsistencias",
]

CAMPOS_SUCESSO = [
    "id_execucao",
    "id",
    "id_ticket",
    "id_cliente",
    "setor",
    "status_anterior",
    "data_abertura",
    "data_hora",
    "mensagem_encontrada",
    "resposta_ixc",
]

CAMPOS_ERRO = [
    "id_execucao",
    "id",
    "id_ticket",
    "data_hora",
    "etapa",
    "categoria",
    "mensagem",
]


def executar_modo_emergencial(
    configuracao,
    input_fn=input,
    listar_fn=None,
    obter_fn=None,
    fechar_fn=None,
):
    if not configuracao.get("modo_emergencial_por_mensagem", False):
        raise RuntimeError("Modo emergencial por mensagem nao esta ativo.")

    resultado = buscar_os_emergenciais(configuracao, listar_fn=listar_fn)
    candidatos, erros = _selecionar_candidatos(
        resultado["registros"],
        resultado["id_execucao"],
    )

    if configuracao["dry_run"]:
        _gravar_resultados([], erros, configuracao)
        print(
            f"Dry-run emergencial: {len(candidatos)} OS(s) seriam fechadas. "
            "Nenhum POST foi enviado."
        )
        return _resumo(resultado, candidatos, [], erros)

    if not candidatos:
        _gravar_resultados([], erros, configuracao)
        return _resumo(resultado, candidatos, [], erros)

    autorizacao = autorizar_fechamento(
        configuracao,
        resultado,
        [registro["id"] for registro in candidatos],
        {
            str(registro.get("id_ticket", "")).strip()
            for registro in candidatos
            if str(registro.get("id_ticket", "")).strip()
        },
        input_fn=input_fn,
    )

    obter_fn = obter_fn or obter_os_por_id
    fechar_fn = fechar_fn or fechar_os
    sucessos = []
    configuracao_execucao = dict(configuracao)
    configuracao_execucao["data_execucao"] = datetime.now().strftime("%d/%m/%Y")

    for registro in candidatos:
        id_os = str(registro["id"])
        try:
            atual = obter_fn(id_os, configuracao["timeout_api_segundos"])
            if str(atual.get("id", "")).strip() != id_os:
                raise IXCAPIError(
                    f"Revalidacao retornou ID diferente para OS {id_os}.",
                    categoria="id_revalidacao_divergente",
                    critico=True,
                )
            problemas = validar_registro_emergencial(atual, configuracao)
            if problemas:
                raise IXCAPIError(
                    f"OS {id_os} inelegivel na revalidacao: {'; '.join(problemas)}",
                    categoria="revalidacao_emergencial",
                )

            resposta = fechar_fn(id_os, configuracao_execucao, autorizacao)
            sucessos.append(
                {
                    "id_execucao": resultado["id_execucao"],
                    "id": id_os,
                    "id_ticket": str(atual.get("id_ticket", "")),
                    "id_cliente": str(atual.get("id_cliente", "")),
                    "setor": str(atual.get("setor", "")),
                    "status_anterior": str(atual.get("status", "")),
                    "data_abertura": str(atual.get("data_abertura", "")),
                    "data_hora": datetime.now().isoformat(timespec="seconds"),
                    "mensagem_encontrada": str(atual.get("mensagem", "")),
                    "resposta_ixc": resposta.get("resposta", ""),
                }
            )
        except Exception as erro:
            erros.append(
                _registro_erro(
                    resultado["id_execucao"],
                    registro,
                    "revalidacao_ou_fechamento",
                    getattr(erro, "categoria", type(erro).__name__),
                    str(erro),
                )
            )
            if getattr(erro, "critico", False):
                break

    _gravar_resultados(sucessos, erros, configuracao)
    return _resumo(resultado, candidatos, sucessos, erros)


def buscar_os_emergenciais(configuracao, listar_fn=None):
    listar_fn = listar_fn or listar_os
    limite = int(configuracao["limite_por_lote"])
    payload = {
        "qtype": "su_oss_chamado.id",
        "query": "0",
        "oper": ">",
        "page": "1",
        "rp": str(limite + 1),
        "grid_param": json.dumps(
            [
                {
                    "TB": "status",
                    "OP": "!=",
                    "P": str(configuracao["status_finalizado"]),
                },
                {
                    "TB": "mensagem",
                    "OP": "LIKE",
                    "P": configuracao["mensagem_busca_emergencial"],
                },
            ]
        ),
        "sortname": "su_oss_chamado.id",
        "sortorder": "asc",
    }
    resposta = listar_fn(payload, configuracao["timeout_api_segundos"])
    registros = list(resposta.get("registros", []))
    id_execucao = uuid4().hex
    gerado_em = datetime.now()

    revisao = []
    for registro in registros:
        linha = dict(registro)
        linha["inconsistencias"] = validar_registro_emergencial(
            registro,
            configuracao,
        )
        revisao.append(linha)

    dados_json = dict(resposta)
    dados_json["registros"] = revisao
    dados_json["_meta_execucao"] = {
        "id_execucao": id_execucao,
        "gerado_em": gerado_em.isoformat(timespec="seconds"),
        "modo": "emergencial_por_mensagem",
    }
    _gravar_json(configuracao["arquivo_json_emergencial"], dados_json)
    _gerar_relatorio_revisao(
        revisao,
        configuracao["relatorio_emergencial_csv"],
    )

    return {
        "total_encontrado": len(revisao),
        "registros": revisao,
        "arquivo_json": configuracao["arquivo_json_emergencial"],
        "relatorio_csv": configuracao["relatorio_emergencial_csv"],
        "id_execucao": id_execucao,
        "gerado_em": gerado_em,
    }


def validar_registro_emergencial(registro, configuracao):
    problemas = []
    id_os = str(registro.get("id", "")).strip()
    status = str(registro.get("status", "")).strip()
    mensagem = str(registro.get("mensagem", ""))
    frase = configuracao["mensagem_busca_emergencial"]

    if not id_os:
        problemas.append("sem_id")
    if status == str(configuracao["status_finalizado"]):
        problemas.append("status_finalizado")
    if frase not in mensagem:
        problemas.append("mensagem_emergencial_ausente")
    return problemas


def _selecionar_candidatos(registros, id_execucao):
    candidatos = []
    erros = []
    ids_vistos = set()
    for registro in registros:
        id_os = str(registro.get("id", "")).strip()
        problemas = list(registro.get("inconsistencias", []))
        if id_os and id_os in ids_vistos:
            problemas.append("id_duplicado_no_lote")
        ids_vistos.add(id_os)

        if problemas:
            erros.append(
                _registro_erro(
                    id_execucao,
                    registro,
                    "validacao_inicial",
                    "inconsistencia",
                    "; ".join(problemas),
                )
            )
        else:
            candidatos.append(registro)
    return candidatos, erros


def _gerar_relatorio_revisao(registros, caminho):
    linhas = []
    for registro in registros:
        linha = {campo: registro.get(campo, "") for campo in CAMPOS_REVISAO}
        linha["inconsistencias"] = "; ".join(
            registro.get("inconsistencias", [])
        )
        linhas.append(linha)
    _gerar_csv(linhas, caminho, CAMPOS_REVISAO)


def _gravar_resultados(sucessos, erros, configuracao):
    _gerar_csv(
        sucessos,
        configuracao["relatorio_emergencial_sucessos_csv"],
        CAMPOS_SUCESSO,
    )
    _gerar_csv(
        erros,
        configuracao["relatorio_emergencial_erros_csv"],
        CAMPOS_ERRO,
    )


def _registro_erro(id_execucao, registro, etapa, categoria, mensagem):
    return {
        "id_execucao": id_execucao,
        "id": str(registro.get("id", "")),
        "id_ticket": str(registro.get("id_ticket", "")),
        "data_hora": datetime.now().isoformat(timespec="seconds"),
        "etapa": etapa,
        "categoria": categoria,
        "mensagem": mensagem,
    }


def _gravar_json(caminho, dados):
    pasta = os.path.dirname(caminho)
    if pasta:
        os.makedirs(pasta, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=4)


def _gerar_csv(registros, caminho, campos):
    pasta = os.path.dirname(caminho)
    if pasta:
        os.makedirs(pasta, exist_ok=True)
    with open(caminho, "w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(
            arquivo,
            fieldnames=campos,
            extrasaction="ignore",
        )
        escritor.writeheader()
        escritor.writerows(registros)


def _resumo(resultado, candidatos, sucessos, erros):
    return {
        "total_encontrado": resultado["total_encontrado"],
        "total_elegiveis": len(candidatos),
        "total_sucessos": len(sucessos),
        "total_erros": len(erros),
        "relatorio_revisao": resultado["relatorio_csv"],
    }
