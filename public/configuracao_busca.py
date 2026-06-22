import json
import os
from datetime import datetime, timedelta


CONFIG_PADRAO = "config/busca_os_config.json"
FORMATO_DATA_CONFIG = "%Y-%m-%d %H:%M:%S"


def carregar_configuracao(caminho_config=CONFIG_PADRAO):
    if not os.path.exists(caminho_config):
        raise FileNotFoundError(f"Arquivo de configuracao nao encontrado: {caminho_config}")

    with open(caminho_config, "r", encoding="utf-8") as arquivo:
        configuracao = json.load(arquivo)

    validar_configuracao(configuracao)
    return configuracao


def validar_configuracao(configuracao):
    campos_obrigatorios = [
        "setores_permitidos",
        "status_finalizado",
        "data_abertura_limite",
        "tecnico_responsavel",
        "limite_por_lote",
        "dry_run",
        "arquivo_json_busca",
        "relatorio_csv",
        "relatorio_sucessos_csv",
        "relatorio_erros_csv",
        "validade_json_minutos",
        "limite_erros_repetidos",
        "mensagem_fechamento",
        "timeout_api_segundos",
    ]

    faltando = [campo for campo in campos_obrigatorios if campo not in configuracao]
    if faltando:
        raise ValueError(f"Campos obrigatorios ausentes na configuracao: {', '.join(faltando)}")

    if not isinstance(configuracao["dry_run"], bool):
        raise ValueError("dry_run deve ser true ou false.")

    if not configuracao["setores_permitidos"]:
        raise ValueError("Informe ao menos um setor permitido.")

    if int(configuracao["limite_por_lote"]) <= 0:
        raise ValueError("limite_por_lote deve ser maior que zero.")

    if int(configuracao["validade_json_minutos"]) <= 0:
        raise ValueError("validade_json_minutos deve ser maior que zero.")

    if int(configuracao["limite_erros_repetidos"]) <= 0:
        raise ValueError("limite_erros_repetidos deve ser maior que zero.")

    if int(configuracao["timeout_api_segundos"]) <= 0:
        raise ValueError("timeout_api_segundos deve ser maior que zero.")

    if not str(configuracao["mensagem_fechamento"]).strip():
        raise ValueError("mensagem_fechamento nao pode ficar vazia.")

    datetime.strptime(configuracao["data_abertura_limite"], FORMATO_DATA_CONFIG)


def data_limite_abertura(configuracao):
    return datetime.strptime(configuracao["data_abertura_limite"], FORMATO_DATA_CONFIG)


def validar_json_recente(caminho_json, validade_minutos):
    return validar_arquivo_recente(caminho_json, validade_minutos, "JSON de busca")


def validar_arquivo_recente(caminho, validade_minutos, descricao="arquivo"):
    if not os.path.exists(caminho):
        raise FileNotFoundError(f"{descricao} nao encontrado: {caminho}")

    modificado_em = datetime.fromtimestamp(os.path.getmtime(caminho))
    limite = datetime.now() - timedelta(minutes=int(validade_minutos))
    if modificado_em < limite:
        raise ValueError(
            f"{descricao} esta antigo. Ultima modificacao: {modificado_em:%Y-%m-%d %H:%M:%S}"
        )

    return modificado_em
