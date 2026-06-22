# script desenvolvido por Guilherme Wallace Souza Costa (https://github.com/guilherme-wallace)

import logging
import os

from public.configuracao_busca import carregar_configuracao
from public.finalizar_OS import finalizar_OS
from public.obter_Dados_OS import obter_dados_OS


caminho = ""
os.makedirs(f"{caminho}src", exist_ok=True)

logging.basicConfig(
    filename=f"{caminho}src/executa_script.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def main():
    try:
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

    except Exception as erro:
        logging.error("Erro durante a execucao do script: %s", erro)
        raise

    logging.info("Execucao do script concluida.")


if __name__ == "__main__":
    main()
