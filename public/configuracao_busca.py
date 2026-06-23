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

    configuracao.setdefault("simulacao_fechamento", False)
    configuracao.setdefault(
        "relatorio_simulacao_sucessos_csv",
        "src/relatorio_simulacao_sucessos.csv",
    )
    configuracao.setdefault(
        "relatorio_simulacao_erros_csv",
        "src/relatorio_simulacao_erros.csv",
    )
    configuracao.setdefault("fechamento_cascata_ativo", False)
    configuracao.setdefault(
        "frase_marcadora_fechamento",
        "OS finalizada em lote via script de fechamento.",
    )
    configuracao.setdefault("max_rodadas_cascata", 5)
    configuracao.setdefault("limite_por_rodada_cascata", 100)
    configuracao.setdefault("intervalo_segundos_entre_rodadas", 5)
    configuracao.setdefault(
        "diretorio_relatorios_cascata",
        "src/relatorios_cascata",
    )
    configuracao.setdefault("modo_emergencial_por_mensagem", False)
    configuracao.setdefault(
        "mensagem_busca_emergencial",
        "OS finalizada em lote via script de fechamento.",
    )
    configuracao.setdefault(
        "arquivo_json_emergencial",
        "src/emergencial_os_encontradas.json",
    )
    configuracao.setdefault(
        "relatorio_emergencial_csv",
        "src/relatorio_emergencial_revisao.csv",
    )
    configuracao.setdefault(
        "relatorio_emergencial_sucessos_csv",
        "src/relatorio_emergencial_sucessos.csv",
    )
    configuracao.setdefault(
        "relatorio_emergencial_erros_csv",
        "src/relatorio_emergencial_erros.csv",
    )

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
        "simulacao_fechamento",
        "arquivo_json_busca",
        "relatorio_csv",
        "relatorio_sucessos_csv",
        "relatorio_erros_csv",
        "relatorio_simulacao_sucessos_csv",
        "relatorio_simulacao_erros_csv",
        "validade_json_minutos",
        "limite_erros_repetidos",
        "mensagem_fechamento",
        "timeout_api_segundos",
        "fechamento_cascata_ativo",
        "frase_marcadora_fechamento",
        "max_rodadas_cascata",
        "limite_por_rodada_cascata",
        "intervalo_segundos_entre_rodadas",
        "diretorio_relatorios_cascata",
        "modo_emergencial_por_mensagem",
        "mensagem_busca_emergencial",
        "arquivo_json_emergencial",
        "relatorio_emergencial_csv",
        "relatorio_emergencial_sucessos_csv",
        "relatorio_emergencial_erros_csv",
    ]

    faltando = [campo for campo in campos_obrigatorios if campo not in configuracao]
    if faltando:
        raise ValueError(f"Campos obrigatorios ausentes na configuracao: {', '.join(faltando)}")

    if not isinstance(configuracao["dry_run"], bool):
        raise ValueError("dry_run deve ser true ou false.")

    if not isinstance(configuracao["simulacao_fechamento"], bool):
        raise ValueError("simulacao_fechamento deve ser true ou false.")

    if configuracao["simulacao_fechamento"] and not configuracao["dry_run"]:
        raise ValueError("A simulacao exige dry_run=true.")

    if not isinstance(configuracao["fechamento_cascata_ativo"], bool):
        raise ValueError("fechamento_cascata_ativo deve ser true ou false.")

    if not isinstance(configuracao["modo_emergencial_por_mensagem"], bool):
        raise ValueError("modo_emergencial_por_mensagem deve ser true ou false.")

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

    if int(configuracao["max_rodadas_cascata"]) <= 0:
        raise ValueError("max_rodadas_cascata deve ser maior que zero.")

    if int(configuracao["limite_por_rodada_cascata"]) <= 0:
        raise ValueError("limite_por_rodada_cascata deve ser maior que zero.")

    if int(configuracao["intervalo_segundos_entre_rodadas"]) < 0:
        raise ValueError("intervalo_segundos_entre_rodadas nao pode ser negativo.")

    if not str(configuracao["frase_marcadora_fechamento"]).strip():
        raise ValueError("frase_marcadora_fechamento nao pode ficar vazia.")

    if not str(configuracao["mensagem_busca_emergencial"]).strip():
        raise ValueError("mensagem_busca_emergencial nao pode ficar vazia.")

    if (
        configuracao["fechamento_cascata_ativo"]
        and configuracao["frase_marcadora_fechamento"]
        not in configuracao["mensagem_fechamento"]
    ):
        raise ValueError(
            "mensagem_fechamento deve conter frase_marcadora_fechamento "
            "quando a cascata estiver ativa."
        )

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
