import csv
import os
from datetime import datetime


CAMPOS_RELATORIO = [
    "id",
    "status",
    "setor",
    "data_abertura",
    "id_cliente",
    "id_contrato_kit",
    "id_assunto",
    "id_tecnico",
    "protocolo",
    "mensagem",
    "inconsistencias",
]

CAMPOS_FECHAMENTO_SUCESSO = [
    "id_execucao",
    "id",
    "data_hora",
    "setor_revalidado",
    "status_anterior",
    "data_abertura",
    "id_tecnico_responsavel",
    "mensagem_fechamento",
    "resposta_ixc",
]

CAMPOS_FECHAMENTO_ERRO = [
    "id_execucao",
    "id",
    "data_hora",
    "etapa",
    "categoria",
    "codigo_http",
    "critico",
    "tentativa_repetida",
    "mensagem",
]


def gerar_relatorio_csv(registros, caminho_csv):
    pasta = os.path.dirname(caminho_csv)
    if pasta:
        os.makedirs(pasta, exist_ok=True)

    with open(caminho_csv, "w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_RELATORIO, extrasaction="ignore")
        escritor.writeheader()
        for registro in registros:
            linha = {campo: registro.get(campo, "") for campo in CAMPOS_RELATORIO}
            linha["inconsistencias"] = "; ".join(registro.get("inconsistencias", []))
            escritor.writerow(linha)


def gerar_relatorios_fechamento(sucessos, erros, configuracao):
    _gerar_csv(
        sucessos,
        configuracao["relatorio_sucessos_csv"],
        CAMPOS_FECHAMENTO_SUCESSO,
    )
    _gerar_csv(
        erros,
        configuracao["relatorio_erros_csv"],
        CAMPOS_FECHAMENTO_ERRO,
    )


def _gerar_csv(registros, caminho_csv, campos):
    pasta = os.path.dirname(caminho_csv)
    if pasta:
        os.makedirs(pasta, exist_ok=True)

    with open(caminho_csv, "w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos, extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(registros)


def validar_registros(registros, configuracao):
    registros_validados = []
    inconsistencias = []

    for registro in registros:
        registro_validado = dict(registro)
        problemas = validar_filtros_os(registro, configuracao)
        id_os = str(registro.get("id", "")).strip()

        for campo in ("id_cliente", "id_assunto", "protocolo"):
            if not str(registro.get(campo, "")).strip():
                problemas.append(f"{campo}_vazio")

        registro_validado["inconsistencias"] = problemas
        if problemas:
            inconsistencias.append({"id": id_os, "problemas": problemas})

        registros_validados.append(registro_validado)

    return registros_validados, inconsistencias


def validar_filtros_os(registro, configuracao):
    setores_permitidos = {str(setor) for setor in configuracao["setores_permitidos"]}
    status_finalizado = str(configuracao["status_finalizado"])
    data_limite = _parse_data_config(configuracao["data_abertura_limite"])
    problemas = []

    id_os = str(registro.get("id", "")).strip()
    status = str(registro.get("status", "")).strip()
    setor = str(registro.get("setor", "")).strip()
    data_abertura_texto = str(registro.get("data_abertura", "")).strip()

    if not id_os:
        problemas.append("sem_id")

    if status == status_finalizado:
        problemas.append("status_finalizado")

    if setor not in setores_permitidos:
        problemas.append("setor_fora_da_configuracao")

    data_abertura = _parse_data_ixc(data_abertura_texto)
    if data_abertura is None:
        problemas.append("data_abertura_invalida")
    elif data_abertura >= data_limite:
        problemas.append("data_abertura_fora_do_limite")

    return problemas


def _parse_data_config(valor):
    return datetime.strptime(valor, "%Y-%m-%d %H:%M:%S")


def _parse_data_ixc(valor):
    formatos = [
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
    ]

    for formato in formatos:
        try:
            return datetime.strptime(valor, formato)
        except ValueError:
            continue

    return None
