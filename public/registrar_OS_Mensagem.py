import requests
import base64
import json
import os
import logging
from route.dadosDeconexao import hostIXC, tokenIXC

def registrar_OS_Mensagem():
    caminho = ''
    logging.basicConfig(filename=f'{caminho}src/finalizar_OS_Mensagem.log',
                       level=logging.INFO,
                       format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        arquivo_entrada = f'{caminho}src/pegaOSResultado.json'
        
        if not os.path.exists(arquivo_entrada):
            logging.error(f"Arquivo {arquivo_entrada} não encontrado")
            print(f"Arquivo {arquivo_entrada} não encontrado")
            return

        with open(arquivo_entrada, 'r', encoding='utf-8') as f:
            dados_os = json.load(f)

        url = f"https://{hostIXC}/webservice/v1/su_oss_chamado_mensagem"
        token = tokenIXC
        
        headers = {
            'Authorization': 'Basic {}'.format(base64.b64encode(token.encode('utf-8')).decode('utf-8')),
            'Content-Type': 'application/json'
        }

        if 'registros' not in dados_os or not dados_os['registros']:
            logging.info("Nenhum registro encontrado para registrar mensagem")
            print("Nenhum registro encontrado para registrar mensagem")
            return

        for registro in dados_os['registros']:
            id_os = registro.get('id', '')
            if not id_os:
                logging.warning("Registro sem ID encontrado, pulando...")
                continue

            payload = {
                "id_chamado": str(id_os),
                "mensagem": "Cobrança sendo realizada pela empresa 2SAFE"
            }

            try:
                response = requests.post(url, 
                                       data=json.dumps(payload), 
                                       headers=headers)
                
                if response.status_code == 200:
                    logging.info(f"Mensagem registrada na OS {id_os} com sucesso")
                    print(f"Mensagem registrada na OS {id_os} com sucesso")
                else:
                    logging.error(f"Erro ao registrar mensagem na OS {id_os}: Status {response.status_code}")
                    print(f"Erro ao registrar mensagem na OS {id_os}: Status {response.status_code}")
                    print(f"Resposta: {response.text}")
                    
            except requests.exceptions.RequestException as e:
                logging.error(f"Erro na requisição para OS {id_os}: {str(e)}")
                print(f"Erro na requisição para OS {id_os}: {str(e)}")

    except Exception as e:
        logging.error(f"Erro geral no script: {str(e)}")
        print(f"Erro geral no script: {str(e)}")

    logging.info("Processo de registrar mensagem concluído")
    print("Processo de registrar mensagem concluído")

if __name__ == "__main__":
    finalizar_OS_Mensagem()