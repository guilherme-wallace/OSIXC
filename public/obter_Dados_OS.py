import json
import os
from datetime import datetime
from uuid import uuid4

from public.configuracao_busca import carregar_configuracao, validar_json_recente
from public.ixc_client import listar_os
from public.relatorio_os import gerar_relatorio_csv, validar_registros


def obter_dados_OS(arquivo_saida_pega_OS_json=None, caminho_config=None):
    configuracao = carregar_configuracao(caminho_config) if caminho_config else carregar_configuracao()
    arquivo_saida_pega_OS_json = arquivo_saida_pega_OS_json or configuracao["arquivo_json_busca"]

    setores = ",".join(str(setor) for setor in configuracao["setores_permitidos"])
    id_execucao = uuid4().hex
    gerado_em = datetime.now()

    payload = {
<<<<<<< Updated upstream
        "qtype": "su_oss_chamado.id",
        "query": "0",
        "oper": ">",
        "page": "1",
        "rp": str(configuracao["limite_por_lote"]),
        "grid_param": json.dumps(
            [
                {
                    "TB": "status",
                    "OP": "!=",
                    "P": str(configuracao["status_finalizado"]),
                },
                {
                    "TB": "setor",
                    "OP": "IN",
                    "P": setores,
                },
                {
                    "TB": "data_abertura",
                    "OP": "<",
                    "P": configuracao["data_abertura_limite"],
                },
            ]
        ),
        "sortname": "su_oss_chamado.id",
        "sortorder": "asc",
=======
        'qtype': 'su_oss_chamado.id',
        'query': '0',
        'oper': '>',
        'page': '1',
        'rp': '10000',
        'grid_param': json.dumps([
            {
            "TB": "mensagem",
            "OP": "L",
            "P": "OS finalizada em lote via script de fechamento."
        }
        ]),
        'sortname': 'su_oss_chamado.id',
        'sortorder': 'asc'
>>>>>>> Stashed changes
    }

    json_data = listar_os(payload, configuracao["timeout_api_segundos"])

    registros = json_data.get("registros", [])
    registros_validados, inconsistencias = validar_registros(registros, configuracao)
    json_data["registros"] = registros_validados
    json_data["_meta_execucao"] = {
        "id_execucao": id_execucao,
        "gerado_em": gerado_em.isoformat(timespec="seconds"),
        "dry_run": configuracao["dry_run"],
    }

    pasta_saida = os.path.dirname(arquivo_saida_pega_OS_json)
    if pasta_saida:
        os.makedirs(pasta_saida, exist_ok=True)

    with open(arquivo_saida_pega_OS_json, "w", encoding="utf-8") as arquivo:
        json.dump(json_data, arquivo, ensure_ascii=False, indent=4)

    validar_json_recente(arquivo_saida_pega_OS_json, configuracao["validade_json_minutos"])
    gerar_relatorio_csv(registros_validados, configuracao["relatorio_csv"])

    print(f"Os dados foram salvos no arquivo JSON '{arquivo_saida_pega_OS_json}'.")
    print(f"Relatorio CSV gerado em '{configuracao['relatorio_csv']}'.")
    print("Etapa de busca concluida. Nenhuma OS foi alterada durante a busca.")
    print(f"Total de OSs encontradas: {len(registros_validados)}.")
    print(f"Registros com inconsistencias: {len(inconsistencias)}.")

    return {
        "total_encontrado": len(registros_validados),
        "total_inconsistencias": len(inconsistencias),
        "arquivo_json": arquivo_saida_pega_OS_json,
        "relatorio_csv": configuracao["relatorio_csv"],
        "dry_run": configuracao["dry_run"],
        "id_execucao": id_execucao,
        "gerado_em": gerado_em,
        "registros": registros_validados,
    }
