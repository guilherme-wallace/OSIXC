from datetime import datetime
from time import perf_counter

from public.fechamento_cascata import executar_cascata_simulada
from public.ixc_client import IXCAPIError, obter_os_por_id
from public.relatorio_os import gerar_relatorios_simulacao, validar_filtros_os
from public.travas_seguranca import confirmar_simulacao


def simular_fechamento(
    configuracao,
    resultado_busca,
    input_fn=input,
    obter_os_fn=None,
    relogio_fn=perf_counter,
):
    obter_os_fn = obter_os_fn or obter_os_por_id
    inicio = relogio_fn()
    registros = resultado_busca.get("registros", [])
    candidatos = []
    erros = []
    ids_vistos = set()

    for registro in registros:
        id_os = str(registro.get("id", "")).strip()
        problemas = validar_filtros_os(registro, configuracao)
        if id_os and id_os in ids_vistos:
            problemas.append("id_duplicado_no_lote")
        ids_vistos.add(id_os)

        if problemas:
            erros.append(
                _erro_simulacao(
                    resultado_busca,
                    id_os,
                    etapa="validacao_inicial",
                    categoria="ignorado",
                    mensagem="; ".join(problemas),
                )
            )
        else:
            candidatos.append(registro)

    confirmar_simulacao(
        configuracao,
        resultado_busca,
        len(candidatos),
        input_fn=input_fn,
    )

    sucessos = []
    erros_revalidacao = 0
    for registro in candidatos:
        id_os = str(registro["id"])
        try:
            os_atual = obter_os_fn(id_os, configuracao["timeout_api_segundos"])
            problemas = validar_filtros_os(os_atual, configuracao)
            if str(os_atual.get("id_ticket", "")).strip() != str(
                registro.get("id_ticket", "")
            ).strip():
                problemas.append("id_ticket_alterado_na_revalidacao")
            if problemas:
                raise IXCAPIError(
                    f"OS {id_os} nao atende mais aos filtros: {'; '.join(problemas)}",
                    categoria="revalidacao_filtros",
                )

            sucessos.append(
                {
                    "id_execucao": resultado_busca["id_execucao"],
                    "id": id_os,
                    "id_ticket": str(os_atual.get("id_ticket", "")),
                    "data_hora": datetime.now().isoformat(timespec="seconds"),
                    "setor_revalidado": os_atual.get("setor", ""),
                    "status_atual": os_atual.get("status", ""),
                    "data_abertura": os_atual.get("data_abertura", ""),
                    "resultado": "SERIA_FECHADA",
                }
            )
        except Exception as erro:
            erros_revalidacao += 1
            erros.append(
                _erro_simulacao(
                    resultado_busca,
                    id_os,
                    etapa="revalidacao",
                    categoria=getattr(erro, "categoria", type(erro).__name__),
                    mensagem=str(erro),
                )
            )

    gerar_relatorios_simulacao(sucessos, erros, configuracao)
    duracao = max(0.0, relogio_fn() - inicio)
    ignorados = len(registros) - len(candidatos)

    cascata = None
    if configuracao.get("fechamento_cascata_ativo", False):
        cascata = executar_cascata_simulada(
            configuracao,
            {
                str(registro.get("id_ticket", "")).strip()
                for registro in candidatos
                if str(registro.get("id_ticket", "")).strip()
            },
            input_fn=input_fn,
        )

    return {
        "total_encontrado": len(registros),
        "total_dentro_lote": len(candidatos),
        "total_seriam_fechadas": len(sucessos),
        "total_erros_revalidacao": erros_revalidacao,
        "total_ignorado": ignorados,
        "tempo_aproximado_segundos": round(duracao, 2),
        "relatorio_sucessos": configuracao["relatorio_simulacao_sucessos_csv"],
        "relatorio_erros": configuracao["relatorio_simulacao_erros_csv"],
        "cascata": cascata,
    }


def _erro_simulacao(resultado_busca, id_os, etapa, categoria, mensagem):
    return {
        "id_execucao": resultado_busca["id_execucao"],
        "id": str(id_os),
        "data_hora": datetime.now().isoformat(timespec="seconds"),
        "etapa": etapa,
        "categoria": categoria,
        "mensagem": mensagem,
    }
