#script desenvolvido por Guilherme Wallace Souza Costa (https://github.com/guilherme-wallace)

import logging
from datetime import datetime
from public.obter_Dados_OS import obter_dados_OS
from public.finalizar_OS_Mensagem import finalizar_OS_Mensagem
from public.finalizar_OS import finalizar_OS
from public.mudar_setor import finalizar_OS_mudar_setor

caminho = ''

logging.basicConfig(filename=f'{caminho}src/executa_script.log', 
                    level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    try:
        logging.info("Início da execução do script.")
        arquivo_saida_pega_OS = f'{caminho}src/pegaOSResultado.json'

        obter_dados_OS(arquivo_saida_pega_OS)
        logging.info(f"Dados do Atendimento obtidos e salvos em {arquivo_saida_pega_OS}.")

        finalizar_OS_mudar_setor()
        #finalizar_OS()
        #finalizar_OS_Mensagem()
        logging.info(f"Script finalizado.")

    except Exception as e:
        logging.error(f"Erro durante a execução do script: {e}")

    logging.info("Execução do script concluída.")

if __name__ == "__main__":
    main()
