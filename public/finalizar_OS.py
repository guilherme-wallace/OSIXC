<<<<<<< Updated upstream
from collections import Counter
=======
import requests
import base64
import json
import os
import logging
from route.dadosDeconexao import hostIXC, tokenIXC
>>>>>>> Stashed changes
from datetime import datetime

from public.ixc_client import IXCAPIError, fechar_os, obter_os_por_id
from public.relatorio_os import gerar_relatorios_fechamento, validar_filtros_os
from public.travas_seguranca import autorizar_fechamento


def finalizar_OS(
    configuracao,
    resultado_busca,
    input_fn=input,
    obter_os_fn=None,
    fechar_os_fn=None,
):
    obter_os_fn = obter_os_fn or obter_os_por_id
    fechar_os_fn = fechar_os_fn or fechar_os

    registros = resultado_busca.get("registros", [])
    candidatos = []
    erros = []
    ids_vistos = set()

<<<<<<< Updated upstream
    for registro in registros:
        problemas = validar_filtros_os(registro, configuracao)
        id_os = str(registro.get("id", "")).strip()
        if id_os and id_os in ids_vistos:
            problemas.append("id_duplicado_no_lote")
        ids_vistos.add(id_os)

        if problemas:
            erros.append(
                _registro_erro(
                    resultado_busca,
                    id_os,
                    etapa="validacao_inicial",
                    categoria="filtros_iniciais",
                    mensagem="; ".join(problemas),
                )
            )
        else:
            candidatos.append(registro)
=======
        for registro in dados_os['registros']:
            id_os = registro.get('id', '')
            if not id_os:
                logging.warning("Registro sem ID encontrado, pulando...")
                continue
            
            data_atual = datetime.now().strftime("%d/%m/%Y")

            payload = {
                "id_chamado": str(id_os),
                "data_inicio": data_atual,
                "data_final": data_atual,
                "proxima_sequencia_forcada": "21",
                "mensagem": "OS finalizada em lote via script de fechamento.",
                "id_tecnico": "133",
                "finaliza_processo_aux": "S",
                "status": "F"
            }
>>>>>>> Stashed changes

    if not candidatos:
        gerar_relatorios_fechamento([], erros, configuracao)
        return _resumo([], erros, interrompido=False)

    autorizacao = autorizar_fechamento(
        configuracao,
        resultado_busca,
        [registro["id"] for registro in candidatos],
        input_fn=input_fn,
    )

    sucessos = []
    contagem_erros = Counter()
    categorias_ignoradas = set()
    interrompido = False
    configuracao_execucao = dict(configuracao)
    configuracao_execucao["data_execucao"] = datetime.now().strftime("%d/%m/%Y")

    for registro in candidatos:
        id_os = str(registro["id"])

        try:
            os_atual = obter_os_fn(id_os, configuracao["timeout_api_segundos"])
            problemas = validar_filtros_os(os_atual, configuracao)
            if problemas:
                raise IXCAPIError(
                    f"OS {id_os} nao atende mais aos filtros: {'; '.join(problemas)}",
                    categoria="revalidacao_filtros",
                )

            resposta = fechar_os_fn(id_os, configuracao_execucao, autorizacao)
            sucessos.append(
                {
                    "id_execucao": resultado_busca["id_execucao"],
                    "id": id_os,
                    "data_hora": datetime.now().isoformat(timespec="seconds"),
                    "setor_revalidado": os_atual.get("setor", ""),
                    "status_anterior": os_atual.get("status", ""),
                    "data_abertura": os_atual.get("data_abertura", ""),
                    "id_tecnico_responsavel": configuracao["tecnico_responsavel"],
                    "mensagem_fechamento": configuracao["mensagem_fechamento"],
                    "resposta_ixc": resposta.get("resposta", ""),
                }
            )

        except IXCAPIError as erro:
            contagem_erros[erro.assinatura] += 1
            repeticoes = contagem_erros[erro.assinatura]
            erros.append(
                _registro_erro(
                    resultado_busca,
                    id_os,
                    etapa="revalidacao_ou_fechamento",
                    categoria=erro.categoria,
                    codigo_http=erro.codigo_http,
                    critico=erro.critico,
                    tentativa_repetida=repeticoes,
                    mensagem=str(erro),
                )
            )

            deve_perguntar = (
                erro.critico
                or repeticoes >= int(configuracao["limite_erros_repetidos"])
            )
            if deve_perguntar and erro.assinatura not in categorias_ignoradas:
                decisao = _perguntar_apos_erro(erro, repeticoes, input_fn)
                if decisao == "ignorar":
                    categorias_ignoradas.add(erro.assinatura)
                elif decisao == "parar":
                    interrompido = True
                    break

        except Exception as erro:
            categoria = f"inesperado:{type(erro).__name__}"
            contagem_erros[categoria] += 1
            repeticoes = contagem_erros[categoria]
            erros.append(
                _registro_erro(
                    resultado_busca,
                    id_os,
                    etapa="erro_inesperado",
                    categoria=categoria,
                    critico=True,
                    tentativa_repetida=repeticoes,
                    mensagem=str(erro),
                )
            )
            if categoria not in categorias_ignoradas:
                decisao = _perguntar_apos_erro(erro, repeticoes, input_fn)
                if decisao == "ignorar":
                    categorias_ignoradas.add(categoria)
                elif decisao == "parar":
                    interrompido = True
                    break

    gerar_relatorios_fechamento(sucessos, erros, configuracao)
    return _resumo(sucessos, erros, interrompido)


def _perguntar_apos_erro(erro, repeticoes, input_fn):
    print("")
    print(f"Erro critico ou repetido {repeticoes} vez(es): {erro}")
    print("[C] Continuar  [I] Ignorar este tipo de erro  [P] Parar")

    while True:
        try:
            resposta = input_fn("> ").strip().lower()
        except EOFError:
            return "parar"

        if resposta in ("c", "continuar"):
            return "continuar"
        if resposta in ("i", "ignorar"):
            return "ignorar"
        if resposta in ("p", "parar"):
            return "parar"
        print("Opcao invalida. Digite C, I ou P.")


def _registro_erro(
    resultado_busca,
    id_os,
    etapa,
    categoria,
    mensagem,
    codigo_http="",
    critico=False,
    tentativa_repetida=1,
):
    return {
        "id_execucao": resultado_busca["id_execucao"],
        "id": str(id_os),
        "data_hora": datetime.now().isoformat(timespec="seconds"),
        "etapa": etapa,
        "categoria": categoria,
        "codigo_http": codigo_http or "",
        "critico": "S" if critico else "N",
        "tentativa_repetida": tentativa_repetida,
        "mensagem": mensagem,
    }


def _resumo(sucessos, erros, interrompido):
    return {
        "total_sucessos": len(sucessos),
        "total_erros": len(erros),
        "interrompido": interrompido,
    }
