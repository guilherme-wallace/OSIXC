import unittest
from unittest.mock import patch

import main


class MainFlowTests(unittest.TestCase):
    def setUp(self):
        self.resultado = {
            "total_encontrado": 1,
            "total_inconsistencias": 0,
            "relatorio_csv": "busca.csv",
        }

    def test_dry_run_nao_chama_fechamento(self):
        with (
            patch("main.carregar_configuracao", return_value={"dry_run": True, "arquivo_json_busca": "busca.json"}),
            patch("main.obter_dados_OS", return_value=self.resultado),
            patch("main.finalizar_OS") as finalizar,
        ):
            main.main()

        finalizar.assert_not_called()

    def test_execucao_real_usa_fluxo_seguro(self):
        configuracao = {"dry_run": False, "arquivo_json_busca": "busca.json"}
        resumo = {
            "total_sucessos": 1,
            "total_erros": 0,
            "interrompido": False,
        }
        with (
            patch("main.carregar_configuracao", return_value=configuracao),
            patch("main.obter_dados_OS", return_value=self.resultado),
            patch("main.finalizar_OS", return_value=resumo) as finalizar,
        ):
            main.main()

        finalizar.assert_called_once_with(configuracao, self.resultado)


if __name__ == "__main__":
    unittest.main()
