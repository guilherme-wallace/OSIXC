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

def deletar_mensagem_atendimento(id_mensagem):
    url = f"https://{hostIXC}/webservice/v1/su_mensagens/{id_mensagem}"

    headers = {
        "Authorization": "Basic {}".format(gerar_token_base64()),
        "Content-Type": "application/json"
    }

    response = requests.delete(url, headers=headers)

    if response.status_code == 200:
        logging.info(f"Mensagem de atendimento {id_mensagem} deletada com sucesso")
        print(f"Mensagem de atendimento {id_mensagem} deletada com sucesso")
        return True

    raise Exception(
        f"Erro ao deletar mensagem de atendimento {id_mensagem}. "
        f"Status {response.status_code}. Resposta: {response.text}"
    )

def deletar_mensagens_atendimentos():
    logging.basicConfig(
    filename=f"{caminho}src/deletar_mensagens_atendimentos.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
    )

    try:
        arquivo_entrada = f"{caminho}src/pegaAtendimentosResultado.json"

        if not os.path.exists(arquivo_entrada):
            logging.error(f"Arquivo {arquivo_entrada} não encontrado")
            print(f"Arquivo {arquivo_entrada} não encontrado")
            return

        with open(arquivo_entrada, "r", encoding="utf-8") as f:
            dados = json.load(f)

        registros = dados.get("registros", [])

        if not registros:
            logging.info("Nenhuma mensagem de atendimento encontrada para deletar")
            print("Nenhuma mensagem de atendimento encontrada para deletar")
            return

        total = len(registros)

        print(f"Total de mensagens encontradas no arquivo: {total}")
        print("ATENÇÃO: este processo irá deletar mensagens de atendimentos no IXC.")
        print(f"Para confirmar, digite exatamente: DELETAR {total} MENSAGENS")

        confirmacao = input("> ").strip()

        if confirmacao != f"DELETAR {total} MENSAGENS":
            print("Confirmação inválida. Processo cancelado.")
            logging.warning("Processo cancelado por confirmação inválida.")
            return

        mensagens_deletadas = 0
        mensagens_ignoradas = 0
        erros = 0

        for registro in registros:
            id_mensagem = str(registro.get("id", "")).strip()
            id_ticket = str(registro.get("id_ticket", "")).strip()
            mensagem = registro.get("mensagem", "")

            if not id_mensagem:
                logging.warning("Registro sem ID de mensagem encontrado, pulando...")
                print("Registro sem ID de mensagem encontrado, pulando...")
                mensagens_ignoradas += 1
                continue

            if not isinstance(mensagem, str) or FRASE_MARCADORA not in mensagem:
                logging.info(f"Mensagem {id_mensagem} ignorada - não contém a frase esperada")
                print(f"Mensagem {id_mensagem} ignorada - não contém a frase esperada")
                mensagens_ignoradas += 1
                continue

            print(f"\nDeletando mensagem {id_mensagem} do atendimento {id_ticket}...")
            logging.info(f"Deletando mensagem {id_mensagem} do atendimento {id_ticket}")

            try:
                deletar_mensagem_atendimento(id_mensagem)
                mensagens_deletadas += 1

            except Exception as e:
                erros += 1
                logging.error(f"Erro ao deletar mensagem {id_mensagem}: {str(e)}")
                print(f"Erro ao deletar mensagem {id_mensagem}: {str(e)}")

        print("\nResumo:")
        print(f"Mensagens deletadas: {mensagens_deletadas}")
        print(f"Mensagens ignoradas: {mensagens_ignoradas}")
        print(f"Erros: {erros}")

        logging.info("Resumo do processo de deleção de mensagens dos atendimentos")
        logging.info(f"Mensagens deletadas: {mensagens_deletadas}")
        logging.info(f"Mensagens ignoradas: {mensagens_ignoradas}")
        logging.info(f"Erros: {erros}")

    except Exception as e:
        logging.error(f"Erro geral no script: {str(e)}")
        print(f"Erro geral no script: {str(e)}")

    logging.info("Processo de deleção de mensagens dos atendimentos concluído")
    print("Processo de deleção de mensagens dos atendimentos concluído")

if __name__ == "__main__":
    deletar_mensagens_atendimentos()