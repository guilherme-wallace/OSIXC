import json
import os
from datetime import timedelta

from public.configuracao_busca import validar_arquivo_recente


_SEGREDO_CAPABILITY = object()


class _AutorizacaoFechamento:
    __slots__ = ("_segredo", "id_execucao", "ids_pendentes")

    def __init__(self, id_execucao, ids_autorizados):
        self._segredo = _SEGREDO_CAPABILITY
        self.id_execucao = id_execucao
        self.ids_pendentes = set(ids_autorizados)


def validar_artefatos_e_lote(configuracao, resultado_busca):
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


def autorizar_fechamento(configuracao, resultado_busca, ids_autorizados, input_fn=input):
    if configuracao["dry_run"] is not False:
        raise RuntimeError("Fechamento real exige dry_run=false.")

    validar_artefatos_e_lote(configuracao, resultado_busca)

    ids_normalizados = [str(id_os) for id_os in ids_autorizados]
    frase = frase_confirmacao(len(ids_normalizados))
    print("")
    print("ATENCAO: esta operacao fecha OSs reais no IXC.")
    print(f"Para confirmar, digite exatamente: {frase}")
    resposta = input_fn("> ").strip()
    if resposta != frase:
        raise RuntimeError("Confirmacao invalida. Nenhuma OS foi fechada.")

    return _AutorizacaoFechamento(
        resultado_busca["id_execucao"],
        ids_normalizados,
    )


def confirmar_simulacao(configuracao, resultado_busca, quantidade, input_fn=input):
    if configuracao["dry_run"] is not True:
        raise RuntimeError("A simulacao exige dry_run=true.")
    if configuracao["simulacao_fechamento"] is not True:
        raise RuntimeError("Modo simulacao_fechamento nao esta ativo.")

    validar_artefatos_e_lote(configuracao, resultado_busca)
    frase = f"SIMULAR {quantidade} OSS"
    print("")
    print("SIMULACAO: nenhum POST de fechamento sera enviado ao IXC.")
    print(f"Para confirmar, digite exatamente: {frase}")
    if input_fn("> ").strip() != frase:
        raise RuntimeError("Confirmacao de simulacao invalida.")


def validar_e_consumir_autorizacao(autorizacao, id_os):
    if (
        not isinstance(autorizacao, _AutorizacaoFechamento)
        or autorizacao._segredo is not _SEGREDO_CAPABILITY
    ):
        raise RuntimeError("Capability de fechamento ausente ou invalida.")

    id_normalizado = str(id_os)
    if id_normalizado not in autorizacao.ids_pendentes:
        raise RuntimeError(
            f"OS {id_normalizado} nao esta autorizada ou ja consumiu a capability."
        )

    autorizacao.ids_pendentes.remove(id_normalizado)


def frase_confirmacao(quantidade):
    return f"FECHAR {quantidade} OSS"


def bloquear_acao_legada(nome_acao):
    raise RuntimeError(
        f"Acao legada bloqueada: {nome_acao}. Use o fluxo seguro em main.py."
    )


bloquear_acao_destrutiva = bloquear_acao_legada
