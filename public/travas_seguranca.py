import json
import os
from datetime import timedelta

from public.configuracao_busca import validar_arquivo_recente


def validar_pre_condicoes_fechamento(configuracao, resultado_busca):
    if configuracao["dry_run"] is not False:
        raise RuntimeError("Fechamento real exige dry_run=false.")

    registros = resultado_busca.get("registros", [])
    limite = int(configuracao["limite_por_lote"])
    if len(registros) > limite:
        raise RuntimeError(
            f"Quantidade encontrada ({len(registros)}) excede limite_por_lote ({limite})."
        )

    arquivo_json = resultado_busca["arquivo_json"]
    arquivo_csv = resultado_busca["relatorio_csv"]
    validade = configuracao["validade_json_minutos"]

    modificado_json = validar_arquivo_recente(arquivo_json, validade, "JSON de busca")
    modificado_csv = validar_arquivo_recente(arquivo_csv, validade, "CSV de busca")

    gerado_em = resultado_busca["gerado_em"]
    tolerancia = gerado_em - timedelta(seconds=2)
    if modificado_json < tolerancia or modificado_csv < tolerancia:
        raise RuntimeError("JSON ou CSV nao pertencem a execucao atual.")

    with open(arquivo_json, "r", encoding="utf-8") as arquivo:
        dados_json = json.load(arquivo)

    meta = dados_json.get("_meta_execucao", {})
    if meta.get("id_execucao") != resultado_busca.get("id_execucao"):
        raise RuntimeError("Identificador do JSON nao corresponde a execucao atual.")

    if os.path.getsize(arquivo_csv) <= 0:
        raise RuntimeError("CSV de busca esta vazio ou invalido.")


def solicitar_confirmacao_fechamento(quantidade, input_fn=input):
    frase = frase_confirmacao(quantidade)
    print("")
    print("ATENCAO: esta operacao fecha OSs reais no IXC.")
    print(f"Para confirmar, digite exatamente: {frase}")
    resposta = input_fn("> ").strip()
    if resposta != frase:
        raise RuntimeError("Confirmacao invalida. Nenhuma OS foi fechada.")


def frase_confirmacao(quantidade):
    return f"FECHAR {quantidade} OSS"


def bloquear_acao_legada(nome_acao):
    raise RuntimeError(
        f"Acao legada bloqueada: {nome_acao}. Use o fluxo seguro em main.py."
    )


bloquear_acao_destrutiva = bloquear_acao_legada
