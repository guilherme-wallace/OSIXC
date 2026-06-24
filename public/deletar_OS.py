import requests
import base64
import json
import os
import logging
from route.dadosDeconexao import hostIXC, tokenIXC


FRASE_MARCADORA = "OS finalizada em lote via script de fechamento."

caminho = ""


def gerar_token_base64():
    token = tokenIXC

    if isinstance(token, str):
        token = token.encode("utf-8")

    return base64.b64encode(token).decode("utf-8")


def listar_mensagens_da_os(id_os):
    url = f"https://{hostIXC}/webservice/v1/su_oss_chamado_mensagem"

    headers = {
        "ixcsoft": "listar",
        "Authorization": "Basic {}".format(gerar_token_base64()),
        "Content-Type": "application/json"
    }

    payload = {
        "qtype": "su_oss_chamado_mensagem.id_chamado",
        "query": str(id_os),
        "oper": "=",
        "page": "1",
        "rp": "1000",
        "sortname": "su_oss_chamado_mensagem.id",
        "sortorder": "desc"
    }

    response = requests.get(
        url,
        data=json.dumps(payload),
        headers=headers
    )

    if response.status_code != 200:
        raise Exception(
            f"Erro ao buscar mensagens da OS {id_os}. "
            f"Status {response.status_code}. Resposta: {response.text}"
        )

    try:
        dados = response.json()
    except ValueError:
        raise Exception(
            f"Erro ao converter resposta das mensagens da OS {id_os} para JSON. "
            f"Resposta: {response.text}"
        )

    return dados.get("registros", [])


def deletar_mensagem(id_mensagem):
    url = f"https://{hostIXC}/webservice/v1/su_oss_chamado_mensagem/{id_mensagem}"

    headers = {
        "Authorization": "Basic {}".format(gerar_token_base64()),
        "Content-Type": "application/json"
    }

    response = requests.delete(url, headers=headers)

    if response.status_code == 200:
        logging.info(f"Mensagem {id_mensagem} deletada com sucesso")
        print(f"Mensagem {id_mensagem} deletada com sucesso")
        return True

    raise Exception(
        f"Erro ao deletar mensagem {id_mensagem}. "
        f"Status {response.status_code}. Resposta: {response.text}"
    )


def deletar_os_por_id(id_os):
    url = f"https://{hostIXC}/webservice/v1/su_oss_chamado/{id_os}"

    headers = {
        "Authorization": "Basic {}".format(gerar_token_base64()),
        "Content-Type": "application/json"
    }

    response = requests.delete(url, headers=headers)

    if response.status_code == 200:
        logging.info(f"OS {id_os} deletada com sucesso")
        print(f"OS {id_os} deletada com sucesso")
        return True

    raise Exception(
        f"Erro ao deletar OS {id_os}. "
        f"Status {response.status_code}. Resposta: {response.text}"
    )


def deletar_OS():
    logging.basicConfig(
        filename=f"{caminho}src/deletar_OS.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    try:
        arquivo_entrada = f"{caminho}src/pegaOSResultado.json"

        if not os.path.exists(arquivo_entrada):
            logging.error(f"Arquivo {arquivo_entrada} não encontrado")
            print(f"Arquivo {arquivo_entrada} não encontrado")
            return

        with open(arquivo_entrada, "r", encoding="utf-8") as f:
            dados_os = json.load(f)

        if "registros" not in dados_os or not dados_os["registros"]:
            logging.info("Nenhuma OS encontrada para deletar")
            print("Nenhuma OS encontrada para deletar")
            return

        os_deletadas = 0
        os_ignoradas = 0
        mensagens_deletadas = 0
        erros = 0

        for registro in dados_os["registros"]:
            id_os = registro.get("id", "")
            mensagem_os = registro.get("mensagem", "")

            if not id_os:
                logging.warning("Registro sem ID encontrado, pulando...")
                print("Registro sem ID encontrado, pulando...")
                os_ignoradas += 1
                continue

            if not isinstance(mensagem_os, str) or FRASE_MARCADORA not in mensagem_os:
                logging.info(f"OS {id_os} ignorada - mensagem não contém a frase esperada")
                print(f"OS {id_os} ignorada - mensagem não contém a frase esperada")
                os_ignoradas += 1
                continue

            print(f"\nProcessando OS {id_os}...")
            logging.info(f"Processando OS {id_os}")

            try:
                mensagens = listar_mensagens_da_os(id_os)

                print(f"Mensagens encontradas na OS {id_os}: {len(mensagens)}")
                logging.info(f"Mensagens encontradas na OS {id_os}: {len(mensagens)}")

                for mensagem in mensagens:
                    id_mensagem = mensagem.get("id", "")

                    if not id_mensagem:
                        logging.warning(f"Mensagem sem ID encontrada na OS {id_os}, pulando...")
                        print(f"Mensagem sem ID encontrada na OS {id_os}, pulando...")
                        continue

                    deletar_mensagem(id_mensagem)
                    mensagens_deletadas += 1

                deletar_os_por_id(id_os)
                os_deletadas += 1

            except Exception as e:
                erros += 1
                logging.error(f"Erro ao processar OS {id_os}: {str(e)}")
                print(f"Erro ao processar OS {id_os}: {str(e)}")

        print("\nResumo:")
        print(f"OSs deletadas: {os_deletadas}")
        print(f"OSs ignoradas: {os_ignoradas}")
        print(f"Mensagens deletadas: {mensagens_deletadas}")
        print(f"Erros: {erros}")

        logging.info("Resumo do processo de deleção")
        logging.info(f"OSs deletadas: {os_deletadas}")
        logging.info(f"OSs ignoradas: {os_ignoradas}")
        logging.info(f"Mensagens deletadas: {mensagens_deletadas}")
        logging.info(f"Erros: {erros}")

    except Exception as e:
        logging.error(f"Erro geral no script de deleção: {str(e)}")
        print(f"Erro geral no script de deleção: {str(e)}")

    logging.info("Processo de deleção concluído")
    print("Processo de deleção concluído")


if __name__ == "__main__":
    deletar_OS()