import requests
import base64
import json
import os
import logging
from route.dadosDeconexao import hostIXC, tokenIXC

FRASE_MARCADORA = "OS finalizada em lote via script de fechamento."
MENSAGEM_REABERTURA = "."
ID_TECNICO_REABERTURA = "96"

caminho = ""

def gerar_token_base64():
    token = tokenIXC

    if isinstance(token, str):
        token = token.encode("utf-8")

    return base64.b64encode(token).decode("utf-8")

def reabrir_OS():
    logging.basicConfig(
    filename=f"{caminho}src/reabrir_OS.log",
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
            logging.info("Nenhum registro encontrado para reabrir")
            print("Nenhum registro encontrado para reabrir")
            return

        url = f"https://{hostIXC}/webservice/v1/su_oss_chamado_reabrir"

        headers = {
            "Authorization": "Basic {}".format(gerar_token_base64()),
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        os_reabertas = 0
        os_ignoradas = 0
        os_com_erro = 0

        for registro in dados_os["registros"]:
            id_os = str(registro.get("id", "")).strip()
            status_os = str(registro.get("status", "")).strip()
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

            if status_os != "F":
                logging.info(f"OS {id_os} ignorada - status atual é '{status_os}', não está finalizada")
                print(f"OS {id_os} ignorada - status atual é '{status_os}', não está finalizada")
                os_ignoradas += 1
                continue

            payload = {
                "id_chamado": str(id_os),
                "id_tecnico": ID_TECNICO_REABERTURA,
                "status": "A",
                "mensagem": MENSAGEM_REABERTURA
            }

            try:
                print(f"Reabrindo OS {id_os}...")
                logging.info(f"Reabrindo OS {id_os}")
                logging.info(f"Payload OS {id_os}: {json.dumps(payload, ensure_ascii=False)}")

                response = requests.post(
                    url,
                    data=json.dumps(payload),
                    headers=headers
                )

                print(f"Status HTTP OS {id_os}: {response.status_code}")
                print(f"Resposta IXC OS {id_os}: {response.text}")

                logging.info(f"Status HTTP OS {id_os}: {response.status_code}")
                logging.info(f"Resposta IXC OS {id_os}: {response.text}")

                if response.status_code == 200:
                    logging.info(f"OS {id_os} reaberta com sucesso")
                    print(f"OS {id_os} reaberta com sucesso")
                    os_reabertas += 1
                else:
                    logging.error(f"Erro ao reabrir OS {id_os}: Status {response.status_code}")
                    print(f"Erro ao reabrir OS {id_os}: Status {response.status_code}")
                    os_com_erro += 1

            except requests.exceptions.RequestException as e:
                logging.error(f"Erro na requisição para OS {id_os}: {str(e)}")
                print(f"Erro na requisição para OS {id_os}: {str(e)}")
                os_com_erro += 1

        print("\nResumo:")
        print(f"OSs reabertas: {os_reabertas}")
        print(f"OSs ignoradas: {os_ignoradas}")
        print(f"OSs com erro: {os_com_erro}")

        logging.info("Resumo do processo de reabertura")
        logging.info(f"OSs reabertas: {os_reabertas}")
        logging.info(f"OSs ignoradas: {os_ignoradas}")
        logging.info(f"OSs com erro: {os_com_erro}")

    except Exception as e:
        logging.error(f"Erro geral no script de reabertura: {str(e)}")
        print(f"Erro geral no script de reabertura: {str(e)}")

    logging.info("Processo de reabertura concluído")
    print("Processo de reabertura concluído")

if __name__ == "__main__":
    reabrir_OS()