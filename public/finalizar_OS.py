import requests
import base64
import json
import os
import logging
from route.dadosDeconexao import hostIXC, tokenIXC

def finalizar_OS():
    caminho = ''
    logging.basicConfig(filename=f'{caminho}src/finalizar_OS.log',
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

        url = f"https://{hostIXC}/webservice/v1/su_oss_chamado_fechar"
        token = tokenIXC
        
        headers = {
            'Authorization': 'Basic {}'.format(base64.b64encode(token).decode('utf-8')),
            'Content-Type': 'application/json'
        }

        if 'registros' not in dados_os or not dados_os['registros']:
            logging.info("Nenhum registro encontrado para finalização")
            print("Nenhum registro encontrado para finalização")
            return

        for registro in dados_os['registros']:
            id_os = registro.get('id', '')
            if not id_os:
                logging.warning("Registro sem ID encontrado, pulando...")
                continue

            payload = {
                "id_chamado": str(id_os),
                "data_inicio": "20/03/2025",
                "data_final": "01/04/2025",
                "mensagem": "Finalização de OS",
                "id_tecnico": "96",
                "finaliza_processo_aux": "S",
                "status": "F"
            }

            try:
                response = requests.post(url, 
                                       data=json.dumps(payload), 
                                       headers=headers)
                
                if response.status_code == 200:
                    logging.info(f"OS {id_os} finalizada com sucesso")
                    print(f"OS {id_os} finalizada com sucesso")
                else:
                    logging.error(f"Erro ao finalizar OS {id_os}: Status {response.status_code}")
                    print(f"Erro ao finalizar OS {id_os}: Status {response.status_code}")
                    print(f"Resposta: {response.text}")
                    
            except requests.exceptions.RequestException as e:
                logging.error(f"Erro na requisição para OS {id_os}: {str(e)}")
                print(f"Erro na requisição para OS {id_os}: {str(e)}")

    except Exception as e:
        logging.error(f"Erro geral no script: {str(e)}")
        print(f"Erro geral no script: {str(e)}")

    logging.info("Processo de finalização concluído")
    print("Processo de finalização concluído")

if __name__ == "__main__":
    finalizar_OS()