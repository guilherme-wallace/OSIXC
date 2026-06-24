# script desenvolvido por Guilherme Wallace Souza Costa (https://github.com/guilherme-wallace)

import logging
import os

from public.configuracao_busca import carregar_configuracao
from public.finalizar_OS import finalizar_OS
<<<<<<< Updated upstream
from public.obter_Dados_OS import obter_dados_OS
=======
from public.mudar_setor import finalizar_OS_mudar_setor
from public.registrar_OS_Mensagem import registrar_OS_Mensagem
from public.deletar_OS import deletar_OS
from public.reabrir_OS import reabrir_OS
from public.obter_Dados_atendimentos import obter_dados_atendimentos
from public.deletar_mensagens_atendimentos import deletar_mensagens_atendimentos
>>>>>>> Stashed changes


caminho = ""
os.makedirs(f"{caminho}src", exist_ok=True)

logging.basicConfig(
    filename=f"{caminho}src/executa_script.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def main():
    try:
<<<<<<< Updated upstream
        logging.info("Inicio da execucao do script.")
        configuracao = carregar_configuracao()

        resultado = obter_dados_OS(configuracao["arquivo_json_busca"])
        logging.info(
            "Busca concluida. Total=%s, inconsistencias=%s, csv=%s",
            resultado["total_encontrado"],
            resultado["total_inconsistencias"],
            resultado["relatorio_csv"],
        )

        if configuracao["dry_run"]:
            logging.info("Dry-run ativo. Nenhuma OS foi fechada.")
            print("Dry-run ativo. Revise o CSV antes de habilitar o fechamento real.")
        else:
            resumo = finalizar_OS(configuracao, resultado)
            logging.info(
                "Fechamento concluido. Sucessos=%s, erros=%s, interrompido=%s",
                resumo["total_sucessos"],
                resumo["total_erros"],
                resumo["interrompido"],
            )
            print(
                "Fechamento concluido: "
                f"{resumo['total_sucessos']} sucesso(s), "
                f"{resumo['total_erros']} erro(s)."
            )
=======
        logging.info("Início da execução do script.")
        arquivo_saida_pega_OS = f'{caminho}src/pegaOSResultado.json'
        arquivo_saida_atendimentos = f'{caminho}src/pegaAtendimentosResultado.json'

        #obter_dados_OS(arquivo_saida_pega_OS)
        obter_dados_atendimentos(arquivo_saida_atendimentos)
        #logging.info(f"Dados do Atendimento obtidos e salvos em {arquivo_saida_pega_OS}.")

        #finalizar_OS_mudar_setor()
        #finalizar_OS()
        #finalizar_OS_Mensagem()
        #reabrir_OS()
        #deletar_OS()
        deletar_mensagens_atendimentos()
        #registrar_OS_Mensagem()
        logging.info(f"Script finalizado.")
>>>>>>> Stashed changes

    except Exception as erro:
        logging.error("Erro durante a execucao do script: %s", erro)
        raise

    logging.info("Execucao do script concluida.")


if __name__ == "__main__":
    main()
