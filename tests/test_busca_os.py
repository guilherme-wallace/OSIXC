import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from public.obter_Dados_OS import obter_dados_OS


class BuscaOSTests(unittest.TestCase):
    def test_busca_mockada_gera_json_csv_e_id_execucao(self):
        with tempfile.TemporaryDirectory() as pasta:
            pasta = Path(pasta)
            config_path = pasta / "config.json"
            json_path = pasta / "busca.json"
            csv_path = pasta / "busca.csv"
            config = {
                "setores_permitidos": ["9", "5"],
                "status_finalizado": "F",
                "data_abertura_limite": "2026-05-01 00:00:00",
                "tecnico_responsavel": "96",
                "limite_por_lote": 100,
                "dry_run": True,
                "arquivo_json_busca": str(json_path),
                "relatorio_csv": str(csv_path),
                "relatorio_sucessos_csv": str(pasta / "sucessos.csv"),
                "relatorio_erros_csv": str(pasta / "erros.csv"),
                "validade_json_minutos": 60,
                "limite_erros_repetidos": 3,
                "mensagem_fechamento": "Teste",
                "timeout_api_segundos": 5,
            }
            config_path.write_text(json.dumps(config), encoding="utf-8")
            resposta = {
                "page": "1",
                "total": "1",
                "registros": [
                    {
                        "id": "123",
                        "status": "A",
                        "setor": "9",
                        "data_abertura": "2026-04-30 10:00:00",
                        "id_cliente": "10",
                        "id_assunto": "20",
                        "protocolo": "ABC",
                    }
                ],
            }

            with patch("public.obter_Dados_OS.listar_os", return_value=resposta) as listar:
                resultado = obter_dados_OS(caminho_config=str(config_path))

            self.assertTrue(json_path.exists())
            self.assertTrue(csv_path.exists())
            self.assertEqual(resultado["total_encontrado"], 1)
            self.assertTrue(resultado["id_execucao"])
            payload = listar.call_args.args[0]
            filtros = json.loads(payload["grid_param"])
            self.assertEqual(payload["rp"], "100")
            self.assertTrue(
                any(
                    filtro["TB"] == "setor" and filtro["P"] == "9,5"
                    for filtro in filtros
                )
            )


if __name__ == "__main__":
    unittest.main()
