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
        "validade_json_minutos",
    ]

    faltando = [campo for campo in campos_obrigatorios if campo not in configuracao]
    if faltando:
        raise ValueError(f"Campos obrigatorios ausentes na configuracao: {', '.join(faltando)}")

    if configuracao["dry_run"] is not True:
        raise ValueError("Esta etapa exige dry_run=true. Acoes destrutivas continuam bloqueadas.")

    if not configuracao["setores_permitidos"]:
        raise ValueError("Informe ao menos um setor permitido.")

    if int(configuracao["limite_por_lote"]) <= 0:
        raise ValueError("limite_por_lote deve ser maior que zero.")

    datetime.strptime(configuracao["data_abertura_limite"], FORMATO_DATA_CONFIG)


def data_limite_abertura(configuracao):
    return datetime.strptime(configuracao["data_abertura_limite"], FORMATO_DATA_CONFIG)


def validar_json_recente(caminho_json, validade_minutos):
    if not os.path.exists(caminho_json):
        raise FileNotFoundError(f"Arquivo JSON de busca nao encontrado: {caminho_json}")

    modificado_em = datetime.fromtimestamp(os.path.getmtime(caminho_json))
    limite = datetime.now() - timedelta(minutes=int(validade_minutos))
    if modificado_em < limite:
        raise ValueError(
            f"Arquivo JSON de busca esta antigo. Ultima modificacao: {modificado_em:%Y-%m-%d %H:%M:%S}"
        )

    return modificado_em
