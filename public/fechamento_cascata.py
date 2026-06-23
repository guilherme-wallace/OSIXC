import csv
import os
from collections import Counter
from datetime import datetime
from time import sleep

from public.ixc_client import (
    IXCAPIError,
    fechar_os,
    listar_os_abertas_por_ticket,
    obter_os_por_id,
)
from public.travas_seguranca import (
    autorizar_ids_cascata,
    obter_tickets_autorizados_cascata,
)


CAMPOS_RELATORIO_CASCATA = [
    "rodada",
    "modo",
    "id_ticket",
    "id",
    "status",
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

    tickets = obter_tickets_autorizados_cascata(autorizacao)
    return _executar_rodadas(
        configuracao=configuracao,
        modo="real",
        tickets_autorizados=tickets,
        autorizacao=autorizacao,
        input_fn=input_fn,
        listar_fn=listar_fn or listar_os_abertas_por_ticket,
        obter_fn=obter_fn or obter_os_por_id,
        fechar_fn=fechar_fn or fechar_os,
        sleep_fn=sleep_fn,
    )


def executar_cascata_simulada(
    configuracao,
    tickets_autorizados,
    input_fn=input,
    listar_fn=None,
    obter_fn=None,
    sleep_fn=sleep,
):
    if not configuracao.get("fechamento_cascata_ativo", False):
        return _resumo_vazio("simulacao")
    if configuracao["dry_run"] is not True or not configuracao["simulacao_fechamento"]:
        raise RuntimeError("Cascata simulada exige dry_run e simulacao ativos.")

    tickets = {str(id_ticket).strip() for id_ticket in tickets_autorizados}
    tickets.discard("")
    return _executar_rodadas(
        configuracao=configuracao,
        modo="simulacao",
        tickets_autorizados=tickets,
        autorizacao=None,
        input_fn=input_fn,
        listar_fn=listar_fn or listar_os_abertas_por_ticket,
        obter_fn=obter_fn or obter_os_por_id,
        fechar_fn=None,
        sleep_fn=sleep_fn,
    )


def _executar_rodadas(
    configuracao,
    modo,
    tickets_autorizados,
    autorizacao,
    input_fn,
    listar_fn,
    obter_fn,
    fechar_fn,
    sleep_fn,
):
    if not tickets_autorizados:
        raise RuntimeError("Nenhum id_ticket elegivel foi autorizado para a cascata.")

    max_rodadas = int(configuracao["max_rodadas_cascata"])
    intervalo = float(configuracao["intervalo_segundos_entre_rodadas"])
    limite = int(configuracao["limite_por_rodada_cascata"])
    id_execucao = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    ids_processados = set()
    contagem_erros = Counter()
    totais = _novo_resumo(modo, tickets_autorizados)

    for rodada in range(1, max_rodadas + 1):
        if intervalo > 0:
            sleep_fn(intervalo)

        totais["rodadas_executadas"] = rodada
        linhas = []
        encontrados = []
        parar = False

        for id_ticket in sorted(tickets_autorizados):
            try:
                registros = list(listar_fn(id_ticket, configuracao))
                totais["total_encontrado"] += len(registros)
                totais["por_ticket"][id_ticket]["encontradas"] += len(registros)
                if registros:
                    totais["por_ticket"][id_ticket]["rodadas_com_atividade"] += 1
                encontrados.extend((id_ticket, registro) for registro in registros)
            except Exception as erro:
                totais["total_erros"] += 1
                totais["por_ticket"][id_ticket]["erros"] += 1
                linhas.append(_linha(rodada, modo, id_ticket, {}, "ERRO", str(erro)))
                assinatura = _assinatura_erro(erro)
                contagem_erros[assinatura] += 1
                if getattr(erro, "critico", False):
                    totais["motivo_parada"] = "erro_critico"
                    parar = True
                    break
                if _erro_repetido(contagem_erros[assinatura], configuracao):
                    if _perguntar_continuacao(erro, input_fn) == "parar":
                        totais["motivo_parada"] = "usuario_solicitou_parada"
                        parar = True
                        break

        if parar:
            _finalizar_rodada(
                configuracao, totais, linhas, rodada, modo, id_execucao, 0
            )
            break

        if not encontrados:
            totais["motivo_parada"] = "nenhuma_os_aberta_nos_atendimentos"
            _finalizar_rodada(
                configuracao, totais, linhas, rodada, modo, id_execucao, 0
            )
            break

        candidatos = []
        for indice, (ticket_pesquisado, registro) in enumerate(encontrados):
            id_os = str(registro.get("id", "")).strip()
            problema = ""
            if indice >= limite:
                problema = "fora_do_limite_da_rodada"
            else:
                problema = _problema_elegibilidade(
                    registro,
                    ticket_pesquisado,
                    tickets_autorizados,
                    configuracao,
                )
            if id_os in ids_processados:
                problema = problema or "id_duplicado_entre_rodadas"

            if problema:
                totais["total_ignorado"] += 1
                totais["por_ticket"][ticket_pesquisado]["ignoradas"] += 1
                linhas.append(
                    _linha(
                        rodada,
                        modo,
                        ticket_pesquisado,
                        registro,
                        "IGNORADA",
                        problema,
                    )
                )
                continue

            ids_processados.add(id_os)
            candidatos.append((ticket_pesquisado, registro))

        if not candidatos:
            totais["motivo_parada"] = "sem_novos_ids_elegiveis"
            _finalizar_rodada(
                configuracao, totais, linhas, rodada, modo, id_execucao, 0
            )
            break

        revalidados = []
        for id_ticket, registro in candidatos:
            id_os = str(registro["id"])
            try:
                atual = obter_fn(id_os, configuracao["timeout_api_segundos"])
                if str(atual.get("id", "")).strip() != id_os:
                    raise IXCAPIError(
                        f"Revalidacao retornou ID diferente para OS {id_os}.",
                        categoria="id_revalidacao_divergente",
                        critico=True,
                    )
                problema = _problema_elegibilidade(
                    atual,
                    id_ticket,
                    tickets_autorizados,
                    configuracao,
                )
                if problema:
                    raise IXCAPIError(
                        f"OS {id_os} inelegivel na revalidacao: {problema}",
                        categoria="revalidacao_cascata",
                    )
                revalidados.append((id_ticket, atual))
            except Exception as erro:
                totais["total_erros"] += 1
                totais["por_ticket"][id_ticket]["erros"] += 1
                linhas.append(
                    _linha(rodada, modo, id_ticket, registro, "ERRO", str(erro))
                )
                assinatura = _assinatura_erro(erro)
                contagem_erros[assinatura] += 1
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
        if modo == "real" and not parar:
            for id_ticket in tickets_autorizados:
                ids_ticket = [
                    registro["id"]
                    for ticket, registro in revalidados
                    if ticket == id_ticket
                ]
                if ids_ticket:
                    autorizar_ids_cascata(autorizacao, id_ticket, ids_ticket)

        for id_ticket, registro in revalidados:
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
                totais["por_ticket"][id_ticket]["fechadas_ou_simuladas"] += 1
                linhas.append(
                    _linha(rodada, modo, id_ticket, registro, resultado, "")
                )
            except Exception as erro:
                totais["total_erros"] += 1
                totais["por_ticket"][id_ticket]["erros"] += 1
                linhas.append(
                    _linha(rodada, modo, id_ticket, registro, "ERRO", str(erro))
                )
                assinatura = _assinatura_erro(erro)
                contagem_erros[assinatura] += 1
                if getattr(erro, "critico", False):
                    totais["motivo_parada"] = "erro_critico"
                    parar = True
                    break
                if _erro_repetido(contagem_erros[assinatura], configuracao):
                    if _perguntar_continuacao(erro, input_fn) == "parar":
                        totais["motivo_parada"] = "usuario_solicitou_parada"
                        parar = True
                        break

        _finalizar_rodada(
            configuracao,
            totais,
            linhas,
            rodada,
            modo,
            id_execucao,
            processados_rodada,
        )
        if parar:
            break
    else:
        totais["motivo_parada"] = "max_rodadas"

    return totais


def _problema_elegibilidade(
    registro,
    ticket_esperado,
    tickets_autorizados,
    configuracao,
):
    id_os = str(registro.get("id", "")).strip()
    status = str(registro.get("status", "")).strip()
    id_ticket = str(registro.get("id_ticket", "")).strip()

    if not id_os:
        return "sem_id"
    if status == str(configuracao["status_finalizado"]):
        return "status_finalizado"
    if not id_ticket:
        return "id_ticket_vazio"
    if id_ticket != str(ticket_esperado):
        return "id_ticket_divergente"
    if id_ticket not in tickets_autorizados:
        return "id_ticket_nao_autorizado"
    return ""


def _finalizar_rodada(
    configuracao,
    totais,
    linhas,
    rodada,
    modo,
    id_execucao,
    processados,
):
    caminho = _gravar_relatorio_rodada(
        configuracao,
        rodada,
        modo,
        linhas,
        id_execucao,
    )
    totais["relatorios"].append(caminho)
    ignorados = sum(1 for linha in linhas if linha["resultado"] == "IGNORADA")
    erros = sum(1 for linha in linhas if linha["resultado"] == "ERRO")
    print(
        f"Cascata {modo} rodada {rodada}: encontrados={len(linhas)}, "
        f"processados={processados}, erros={erros}, ignorados={ignorados}"
    )


def _erro_repetido(repeticoes, configuracao):
    return repeticoes >= int(configuracao["limite_erros_repetidos"])


def _perguntar_continuacao(erro, input_fn):
    print(f"Erro repetido na cascata: {erro}")
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


def _linha(rodada, modo, id_ticket, registro, resultado, erro):
    return {
        "rodada": rodada,
        "modo": modo,
        "id_ticket": str(id_ticket),
        "id": str(registro.get("id", "")),
        "status": str(registro.get("status", "")),
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


def _novo_resumo(modo, tickets_autorizados):
    return {
        "modo": modo,
        "ativo": True,
        "rodadas_executadas": 0,
        "total_encontrado": 0,
        "total_fechado_ou_simulado": 0,
        "total_erros": 0,
        "total_ignorado": 0,
        "motivo_parada": "max_rodadas",
        "relatorios": [],
        "por_ticket": {
            id_ticket: {
                "encontradas": 0,
                "fechadas_ou_simuladas": 0,
                "erros": 0,
                "ignoradas": 0,
                "rodadas_com_atividade": 0,
            }
            for id_ticket in sorted(tickets_autorizados)
        },
    }


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
        "por_ticket": {},
    }
