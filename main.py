# script desenvolvido por Guilherme Wallace Souza Costa (https://github.com/guilherme-wallace)

import logging
import os

from public.configuracao_busca import carregar_configuracao
from public.finalizar_OS import finalizar_OS
from public.obter_Dados_OS import obter_dados_OS
from public.simular_fechamento import simular_fechamento


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

        if configuracao.get("simulacao_fechamento", False):
            resumo = simular_fechamento(configuracao, resultado)
            logging.info("Simulacao concluida: %s", resumo)
            print("")
            print("Resumo da simulacao:")
            print(f"OSs encontradas: {resumo['total_encontrado']}")
            print(f"OSs dentro do lote: {resumo['total_dentro_lote']}")
            print(f"OSs que seriam fechadas: {resumo['total_seriam_fechadas']}")
            print(f"Erros de revalidacao: {resumo['total_erros_revalidacao']}")
            print(f"OSs ignoradas: {resumo['total_ignorado']}")
            print(
                "Tempo aproximado: "
                f"{resumo['tempo_aproximado_segundos']:.2f} segundo(s)"
            )
            _mostrar_resumo_cascata(resumo.get("cascata"))
        elif configuracao["dry_run"]:
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
            _mostrar_resumo_cascata(resumo.get("cascata"))

    except Exception as erro:
        logging.error("Erro durante a execucao do script: %s", erro)
        raise

    logging.info("Execucao do script concluida.")


def _mostrar_resumo_cascata(cascata):
    if not cascata or not cascata.get("ativo"):
        return
    print("")
    print("Resumo da cascata:")
    print(f"Rodadas executadas: {cascata['rodadas_executadas']}")
    print(f"OSs encontradas: {cascata['total_encontrado']}")
    print(
        "OSs fechadas ou simuladas: "
        f"{cascata['total_fechado_ou_simulado']}"
    )
    print(f"Erros: {cascata['total_erros']}")
    print(f"Ignoradas: {cascata['total_ignorado']}")
    print(f"Motivo da parada: {cascata['motivo_parada']}")


if __name__ == "__main__":
    main()
