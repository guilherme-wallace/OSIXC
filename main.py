# script desenvolvido por Guilherme Wallace Souza Costa (https://github.com/guilherme-wallace)

import logging
import os

from public.configuracao_busca import carregar_configuracao
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
        logging.info("Inicio da execucao do script em modo dry-run.")
        configuracao = carregar_configuracao()

        if configuracao["dry_run"] is not True:
            raise ValueError("dry_run deve permanecer true nesta etapa da refatoracao.")

        resultado = obter_dados_OS(configuracao["arquivo_json_busca"])
        logging.info(
            "Busca concluida em dry-run. Total=%s, inconsistencias=%s, csv=%s",
            resultado["total_encontrado"],
            resultado["total_inconsistencias"],
            resultado["relatorio_csv"],
        )
        logging.info("Script finalizado sem executar acoes destrutivas.")

    except Exception as erro:
        logging.error("Erro durante a execucao do script: %s", erro)
        raise

    logging.info("Execucao do script concluida.")


if __name__ == "__main__":
    main()
