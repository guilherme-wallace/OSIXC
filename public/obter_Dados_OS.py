import base64
import json
import os
import urllib.request

from public.configuracao_busca import carregar_configuracao, validar_json_recente
from public.relatorio_os import gerar_relatorio_csv, validar_registros
from route.dadosDeconexao import hostIntranet, tokenIXC, urlIXC


def obter_dados_OS(arquivo_saida_pega_OS_json=None, caminho_config=None):
    configuracao = carregar_configuracao(caminho_config) if caminho_config else carregar_configuracao()
    arquivo_saida_pega_OS_json = arquivo_saida_pega_OS_json or configuracao["arquivo_json_busca"]

    host = hostIntranet
    url = urlIXC.format(host)
    setores = ",".join(str(setor) for setor in configuracao["setores_permitidos"])

    payload = {
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
    }

    headers = {
        "ixcsoft": "listar",
        "Authorization": "Basic {}".format(_codificar_token(tokenIXC)),
        "Content-Type": "application/json",
    }

    texto_resposta = _consultar_ixc(url, payload, headers)

    try:
        json_data = json.loads(texto_resposta)
    except ValueError as erro:
        print(f"Erro ao processar a resposta como JSON: {erro}")
        print(f"Resposta bruta: {texto_resposta}")
        raise

    registros = json_data.get("registros", [])
    registros_validados, inconsistencias = validar_registros(registros, configuracao)
    json_data["registros"] = registros_validados

    pasta_saida = os.path.dirname(arquivo_saida_pega_OS_json)
    if pasta_saida:
        os.makedirs(pasta_saida, exist_ok=True)

    with open(arquivo_saida_pega_OS_json, "w", encoding="utf-8") as arquivo:
        json.dump(json_data, arquivo, ensure_ascii=False, indent=4)

    validar_json_recente(arquivo_saida_pega_OS_json, configuracao["validade_json_minutos"])
    gerar_relatorio_csv(registros_validados, configuracao["relatorio_csv"])

    print(f"Os dados foram salvos no arquivo JSON '{arquivo_saida_pega_OS_json}'.")
    print(f"Relatorio CSV gerado em '{configuracao['relatorio_csv']}'.")
    print("Dry-run obrigatorio ativo. Nenhuma OS foi alterada.")
    print(f"Total de OSs encontradas: {len(registros_validados)}.")
    print(f"Registros com inconsistencias: {len(inconsistencias)}.")

    return {
        "total_encontrado": len(registros_validados),
        "total_inconsistencias": len(inconsistencias),
        "arquivo_json": arquivo_saida_pega_OS_json,
        "relatorio_csv": configuracao["relatorio_csv"],
        "dry_run": configuracao["dry_run"],
    }


def _codificar_token(token):
    if isinstance(token, str):
        token = token.encode("utf-8")
    return base64.b64encode(token).decode("utf-8")


def _consultar_ixc(url, payload, headers):
    dados = json.dumps(payload).encode("utf-8")
    requisicao = urllib.request.Request(url, data=dados, headers=headers, method="GET")
    with urllib.request.urlopen(requisicao, timeout=30) as resposta:
        return resposta.read().decode("utf-8")
