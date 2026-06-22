import csv
import os
from collections import Counter
from datetime import datetime
from time import sleep

from public.ixc_client import (
    IXCAPIError,
    fechar_os,
    listar_os_cascata,
    obter_os_por_id,
)
from public.travas_seguranca import autorizar_ids_cascata


CAMPOS_RELATORIO_CASCATA = [
    "rodada",
    "modo",
    "id",
    "status",
    "mensagem",
    "resultado",
    "erro",
    "data_hora",
]


def executar_cascata_real(
    configuracao,
    autorizacao,
    input_fn=input,
    listar_fn=None,
    obter_fn=None,
    fechar_fn=None,
    sleep_fn=sleep,
):
    if not configuracao.get("fechamento_cascata_ativo", False):
        return _resumo_vazio("real")
    if configuracao["dry_run"] is not False:
        raise RuntimeError("Cascata real exige dry_run=false.")

    listar_fn = listar_fn or listar_os_cascata
    obter_fn = obter_fn or obter_os_por_id
    fechar_fn = fechar_fn or fechar_os
    return _executar_rodadas(
        configuracao=configuracao,
        modo="real",
        autorizacao=autorizacao,
        input_fn=input_fn,
        listar_fn=listar_fn,
        obter_fn=obter_fn,
        fechar_fn=fechar_fn,
        sleep_fn=sleep_fn,
    )


def executar_cascata_simulada(
    configuracao,
    input_fn=input,
    listar_fn=None,
    obter_fn=None,
    sleep_fn=sleep,
):
    if not configuracao.get("fechamento_cascata_ativo", False):
        return _resumo_vazio("simulacao")
    if configuracao["dry_run"] is not True or not configuracao["simulacao_fechamento"]:
        raise RuntimeError("Cascata simulada exige dry_run e simulacao ativos.")

    listar_fn = listar_fn or listar_os_cascata
    obter_fn = obter_fn or obter_os_por_id
    return _executar_rodadas(
        configuracao=configuracao,
        modo="simulacao",
        autorizacao=None,
        input_fn=input_fn,
        listar_fn=listar_fn,
        obter_fn=obter_fn,
        fechar_fn=None,
        sleep_fn=sleep_fn,
    )


def _executar_rodadas(
    configuracao,
    modo,
    autorizacao,
    input_fn,
    listar_fn,
    obter_fn,
    fechar_fn,
    sleep_fn,
):
    max_rodadas = int(configuracao["max_rodadas_cascata"])
    intervalo = float(configuracao["intervalo_segundos_entre_rodadas"])
    limite = int(configuracao["limite_por_rodada_cascata"])
    id_execucao = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    ids_processados = set()
    contagem_erros = Counter()
    totais = {
        "modo": modo,
        "ativo": True,
        "rodadas_executadas": 0,
        "total_encontrado": 0,
        "total_fechado_ou_simulado": 0,
        "total_erros": 0,
        "total_ignorado": 0,
        "motivo_parada": "max_rodadas",
        "relatorios": [],
    }

    for rodada in range(1, max_rodadas + 1):
        if intervalo > 0:
            sleep_fn(intervalo)

        totais["rodadas_executadas"] = rodada
        try:
            registros = list(listar_fn(configuracao))
        except Exception as erro:
            linha = _linha(rodada, modo, {}, "ERRO", str(erro))
            caminho = _gravar_relatorio_rodada(
                configuracao,
                rodada,
                modo,
                [linha],
                id_execucao,
            )
            totais["relatorios"].append(caminho)
            totais["total_erros"] += 1
            totais["motivo_parada"] = "erro_na_busca"
            _mostrar_resumo_rodada(rodada, 0, 0, 1, 0, modo)
            break

        totais["total_encontrado"] += len(registros)

        if not registros:
            caminho = _gravar_relatorio_rodada(
                configuracao,
                rodada,
                modo,
                [],
                id_execucao,
            )
            totais["relatorios"].append(caminho)
            totais["motivo_parada"] = "nenhuma_os_marcada"
            _mostrar_resumo_rodada(rodada, 0, 0, 0, 0, modo)
            break

        linhas = []
        candidatos = []
        for indice, registro in enumerate(registros):
            id_os = str(registro.get("id", "")).strip()
            problema = ""
            if indice >= limite:
                problema = "fora_do_limite_da_rodada"
            else:
                problema = _problema_elegibilidade(registro, configuracao)

            if id_os in ids_processados:
                problema = problema or "id_duplicado_entre_rodadas"

            if problema:
                totais["total_ignorado"] += 1
                linhas.append(_linha(rodada, modo, registro, "IGNORADA", problema))
                continue

            ids_processados.add(id_os)
            candidatos.append(registro)

        if not candidatos:
            caminho = _gravar_relatorio_rodada(
                configuracao,
                rodada,
                modo,
                linhas,
                id_execucao,
            )
            totais["relatorios"].append(caminho)
            totais["motivo_parada"] = "sem_novos_ids_elegiveis"
            _mostrar_resumo_rodada(
                rodada, len(registros), 0, 0, len(linhas), modo
            )
            break

        revalidados = []
        parar = False
        for registro in candidatos:
            id_os = str(registro["id"])
            try:
                atual = obter_fn(id_os, configuracao["timeout_api_segundos"])
                problema = _problema_elegibilidade(atual, configuracao)
                if problema:
                    raise IXCAPIError(
                        f"OS {id_os} inelegivel na revalidacao: {problema}",
                        categoria="revalidacao_cascata",
                    )
                revalidados.append(atual)
            except Exception as erro:
                totais["total_erros"] += 1
                assinatura = _assinatura_erro(erro)
                contagem_erros[assinatura] += 1
                linhas.append(_linha(rodada, modo, registro, "ERRO", str(erro)))

                if getattr(erro, "critico", False):
                    totais["motivo_parada"] = "erro_critico"
                    parar = True
                    break
                if _erro_repetido(contagem_erros[assinatura], configuracao):
                    if _perguntar_continuacao(erro, input_fn) == "parar":
                        totais["motivo_parada"] = "usuario_solicitou_parada"
                        parar = True
                        break

        processados_rodada = 0
        if modo == "real" and revalidados and not parar:
            autorizar_ids_cascata(
                autorizacao,
                [registro["id"] for registro in revalidados],
            )

        for registro in revalidados:
            if parar:
                break
            id_os = str(registro["id"])
            try:
                if modo == "real":
                    config_execucao = dict(configuracao)
                    config_execucao["data_execucao"] = datetime.now().strftime(
                        "%d/%m/%Y"
                    )
                    fechar_fn(id_os, config_execucao, autorizacao)
                    resultado = "FECHADA"
                else:
                    resultado = "SERIA_FECHADA"

                processados_rodada += 1
                totais["total_fechado_ou_simulado"] += 1
                linhas.append(_linha(rodada, modo, registro, resultado, ""))
            except Exception as erro:
                totais["total_erros"] += 1
                assinatura = _assinatura_erro(erro)
                contagem_erros[assinatura] += 1
                linhas.append(_linha(rodada, modo, registro, "ERRO", str(erro)))
                if getattr(erro, "critico", False):
                    totais["motivo_parada"] = "erro_critico"
                    parar = True
                    break
                if _erro_repetido(contagem_erros[assinatura], configuracao):
                    if _perguntar_continuacao(erro, input_fn) == "parar":
                        totais["motivo_parada"] = "usuario_solicitou_parada"
                        parar = True
                        break

        caminho = _gravar_relatorio_rodada(
            configuracao,
            rodada,
            modo,
            linhas,
            id_execucao,
        )
        totais["relatorios"].append(caminho)
        ignorados_rodada = sum(1 for linha in linhas if linha["resultado"] == "IGNORADA")
        erros_rodada = sum(1 for linha in linhas if linha["resultado"] == "ERRO")
        _mostrar_resumo_rodada(
            rodada,
            len(registros),
            processados_rodada,
            erros_rodada,
            ignorados_rodada,
            modo,
        )

        if parar:
            break
    else:
        totais["motivo_parada"] = "max_rodadas"

    return totais


def _problema_elegibilidade(registro, configuracao):
    id_os = str(registro.get("id", "")).strip()
    status = str(registro.get("status", "")).strip()
    mensagem = str(registro.get("mensagem", ""))
    marcador = configuracao["frase_marcadora_fechamento"]

    if not id_os:
        return "sem_id"
    if status == str(configuracao["status_finalizado"]):
        return "status_finalizado"
    if marcador not in mensagem:
        return "frase_marcadora_ausente"
    return ""


def _erro_repetido(repeticoes, configuracao):
    return repeticoes >= int(configuracao["limite_erros_repetidos"])


def _perguntar_continuacao(erro, input_fn):
    print(f"Erro critico ou repetido na cascata: {erro}")
    print("[C] Continuar  [P] Parar")
    while True:
        try:
            resposta = input_fn("> ").strip().lower()
        except EOFError:
            return "parar"
        if resposta in ("c", "continuar"):
            return "continuar"
        if resposta in ("p", "parar"):
            return "parar"
        print("Opcao invalida. Digite C ou P.")


def _assinatura_erro(erro):
    return getattr(erro, "assinatura", type(erro).__name__)


def _linha(rodada, modo, registro, resultado, erro):
    return {
        "rodada": rodada,
        "modo": modo,
        "id": str(registro.get("id", "")),
        "status": str(registro.get("status", "")),
        "mensagem": str(registro.get("mensagem", "")),
        "resultado": resultado,
        "erro": erro,
        "data_hora": datetime.now().isoformat(timespec="seconds"),
    }


def _gravar_relatorio_rodada(
    configuracao,
    rodada,
    modo,
    linhas,
    id_execucao,
):
    diretorio = configuracao["diretorio_relatorios_cascata"]
    os.makedirs(diretorio, exist_ok=True)
    caminho = os.path.join(
        diretorio,
        f"cascata_{modo}_{id_execucao}_rodada_{rodada:02d}.csv",
    )
    with open(caminho, "w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_RELATORIO_CASCATA)
        escritor.writeheader()
        escritor.writerows(linhas)
    return caminho


def _mostrar_resumo_rodada(rodada, encontrados, processados, erros, ignorados, modo):
    print(
        f"Cascata {modo} rodada {rodada}: encontrados={encontrados}, "
        f"processados={processados}, erros={erros}, ignorados={ignorados}"
    )


def _resumo_vazio(modo):
    return {
        "modo": modo,
        "ativo": False,
        "rodadas_executadas": 0,
        "total_encontrado": 0,
        "total_fechado_ou_simulado": 0,
        "total_erros": 0,
        "total_ignorado": 0,
        "motivo_parada": "cascata_desativada",
        "relatorios": [],
    }
