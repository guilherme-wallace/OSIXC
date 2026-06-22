import base64
import json
import urllib.error
import urllib.request

from public.travas_seguranca import validar_e_consumir_autorizacao
from route.dadosDeconexao import hostIXC, hostIntranet, tokenIXC, urlIXC


class IXCAPIError(RuntimeError):
    def __init__(self, mensagem, codigo_http=None, categoria="api", critico=False):
        super().__init__(mensagem)
        self.codigo_http = codigo_http
        self.categoria = categoria
        self.critico = critico

    @property
    def assinatura(self):
        return f"{self.categoria}:{self.codigo_http or 'sem_status'}"


def listar_os(payload, timeout_segundos):
    url = urlIXC.format(hostIntranet)
    headers = _headers_listagem()
    texto = _requisicao_json(
        url=url,
        metodo="GET",
        payload=payload,
        headers=headers,
        timeout_segundos=timeout_segundos,
    )
    return _carregar_json(texto, "listagem de OS")


def obter_os_por_id(id_os, timeout_segundos):
    payload = {
        "qtype": "su_oss_chamado.id",
        "query": str(id_os),
        "oper": "=",
        "page": "1",
        "rp": "1",
        "sortname": "su_oss_chamado.id",
        "sortorder": "asc",
    }
    resposta = listar_os(payload, timeout_segundos)
    registros = resposta.get("registros", [])
    if not registros:
        raise IXCAPIError(
            f"OS {id_os} nao foi encontrada durante a revalidacao.",
            categoria="os_nao_encontrada",
        )
    registro = registros[0]
    id_retornado = str(registro.get("id", "")).strip()
    if id_retornado != str(id_os):
        raise IXCAPIError(
            f"IXC retornou OS {id_retornado or 'sem_id'} ao revalidar OS {id_os}.",
            categoria="id_revalidacao_divergente",
            critico=True,
        )
    return registro


def fechar_os(id_os, configuracao, autorizacao=None):
    validar_e_consumir_autorizacao(autorizacao, id_os)

    url = f"https://{hostIXC}/webservice/v1/su_oss_chamado_fechar"
    payload = {
        "id_chamado": str(id_os),
        "data_inicio": configuracao["data_execucao"],
        "data_final": configuracao["data_execucao"],
        "mensagem": configuracao["mensagem_fechamento"],
        "id_tecnico": str(configuracao["tecnico_responsavel"]),
        "finaliza_processo_aux": "S",
        "status": str(configuracao["status_finalizado"]),
    }
    texto = _requisicao_json(
        url=url,
        metodo="POST",
        payload=payload,
        headers=_headers_autenticacao(),
        timeout_segundos=configuracao["timeout_api_segundos"],
    )
    _validar_resposta_fechamento(texto)
    return {
        "id": str(id_os),
        "payload": payload,
        "resposta": texto,
    }


def _requisicao_json(url, metodo, payload, headers, timeout_segundos):
    dados = json.dumps(payload).encode("utf-8")
    requisicao = urllib.request.Request(url, data=dados, headers=headers, method=metodo)

    try:
        with urllib.request.urlopen(requisicao, timeout=int(timeout_segundos)) as resposta:
            return resposta.read().decode("utf-8")
    except urllib.error.HTTPError as erro:
        corpo = erro.read().decode("utf-8", errors="replace")
        critico = erro.code in (401, 403)
        raise IXCAPIError(
            f"IXC respondeu HTTP {erro.code}: {corpo}",
            codigo_http=erro.code,
            categoria="autenticacao" if critico else "http",
            critico=critico,
        ) from erro
    except urllib.error.URLError as erro:
        raise IXCAPIError(
            f"Falha de conexao com o IXC: {erro.reason}",
            categoria="conexao",
        ) from erro
    except TimeoutError as erro:
        raise IXCAPIError(
            "Tempo limite excedido ao consultar o IXC.",
            categoria="timeout",
        ) from erro


def _carregar_json(texto, contexto):
    try:
        return json.loads(texto)
    except ValueError as erro:
        raise IXCAPIError(
            f"Resposta invalida do IXC durante {contexto}.",
            categoria="resposta_invalida",
            critico=True,
        ) from erro


def _validar_resposta_fechamento(texto):
    try:
        resposta = json.loads(texto)
    except (TypeError, ValueError):
        return

    if not isinstance(resposta, dict):
        return

    tipo = str(resposta.get("type", resposta.get("tipo", ""))).lower()
    status = str(resposta.get("status", "")).lower()
    sucesso = resposta.get("success", resposta.get("sucesso"))
    possui_erro = bool(resposta.get("error", resposta.get("erro")))

    if tipo in ("error", "erro", "danger", "failure", "falha"):
        possui_erro = True
    if status in ("error", "erro", "failure", "falha"):
        possui_erro = True
    if sucesso is False:
        possui_erro = True

    if possui_erro:
        raise IXCAPIError(
            f"IXC recusou o fechamento: {texto}",
            categoria="resposta_fechamento",
        )


def _headers_listagem():
    headers = _headers_autenticacao()
    headers["ixcsoft"] = "listar"
    return headers


def _headers_autenticacao():
    token = tokenIXC.encode("utf-8") if isinstance(tokenIXC, str) else tokenIXC
    return {
        "Authorization": f"Basic {base64.b64encode(token).decode('utf-8')}",
        "Content-Type": "application/json",
    }
