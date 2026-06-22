import csv
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import main
from public.simular_fechamento import simular_fechamento


class SimulacaoFechamentoTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.pasta = Path(self.temp_dir.name)
        self.configuracao = {
            "setores_permitidos": ["9", "5"],
            "status_finalizado": "F",
            "data_abertura_limite": "2026-05-01 00:00:00",
            "tecnico_responsavel": "96",
            "limite_por_lote": 100,
            "dry_run": True,
            "simulacao_fechamento": True,
            "arquivo_json_busca": str(self.pasta / "busca.json"),
            "relatorio_csv": str(self.pasta / "busca.csv"),
            "relatorio_sucessos_csv": str(self.pasta / "sucessos.csv"),
            "relatorio_erros_csv": str(self.pasta / "erros.csv"),
            "relatorio_simulacao_sucessos_csv": str(self.pasta / "simulacao_sucessos.csv"),
            "relatorio_simulacao_erros_csv": str(self.pasta / "simulacao_erros.csv"),
            "validade_json_minutos": 60,
            "limite_erros_repetidos": 3,
            "mensagem_fechamento": "Teste",
            "timeout_api_segundos": 5,
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_simulacao_revalida_e_gera_relatorios_sem_post(self):
        resultado = self._criar_resultado([self._os("1"), self._os("2")])
        obter = Mock(side_effect=[self._os("1"), self._os("2", status="F")])

        with patch("public.ixc_client.fechar_os") as fechar:
            resumo = simular_fechamento(
                self.configuracao,
                resultado,
                input_fn=lambda _: "SIMULAR 2 OSS",
                obter_os_fn=obter,
                relogio_fn=Mock(side_effect=[10.0, 12.5]),
            )

        fechar.assert_not_called()
        self.assertEqual(obter.call_count, 2)
        self.assertEqual(resumo["total_seriam_fechadas"], 1)
        self.assertEqual(resumo["total_erros_revalidacao"], 1)
        self.assertEqual(resumo["tempo_aproximado_segundos"], 2.5)
        self.assertEqual(self._contar_linhas("simulacao_sucessos.csv"), 1)
        self.assertEqual(self._contar_linhas("simulacao_erros.csv"), 1)

    def test_simulacao_respeita_limite_por_lote(self):
        self.configuracao["limite_por_lote"] = 1
        resultado = self._criar_resultado([self._os("1"), self._os("2")])
        with self.assertRaisesRegex(RuntimeError, "excede limite_por_lote"):
            simular_fechamento(self.configuracao, resultado, input_fn=lambda _: "SIMULAR 2 OSS")

    def test_confirmacao_invalida_nao_revalida(self):
        resultado = self._criar_resultado([self._os("1")])
        obter = Mock()
        with self.assertRaisesRegex(RuntimeError, "Confirmacao de simulacao invalida"):
            simular_fechamento(
                self.configuracao,
                resultado,
                input_fn=lambda _: "NAO SIMULAR",
                obter_os_fn=obter,
            )
        obter.assert_not_called()

    def test_main_simula_sem_chamar_fechamento_real(self):
        configuracao = {
            "dry_run": True,
            "simulacao_fechamento": True,
            "arquivo_json_busca": "busca.json",
        }
        resultado_busca = {
            "total_encontrado": 1,
            "total_inconsistencias": 0,
            "relatorio_csv": "busca.csv",
        }
        resumo = {
            "total_encontrado": 1,
            "total_dentro_lote": 1,
            "total_seriam_fechadas": 1,
            "total_erros_revalidacao": 0,
            "total_ignorado": 0,
            "tempo_aproximado_segundos": 0.1,
        }
        with (
            patch("main.carregar_configuracao", return_value=configuracao),
            patch("main.obter_dados_OS", return_value=resultado_busca),
            patch("main.simular_fechamento", return_value=resumo) as simular,
            patch("main.finalizar_OS") as finalizar,
        ):
            main.main()
        simular.assert_called_once_with(configuracao, resultado_busca)
        finalizar.assert_not_called()

    def test_simulacao_rejeita_json_antigo(self):
        resultado = self._criar_resultado([self._os("1")])
        antigo = (datetime.now() - timedelta(hours=2)).timestamp()
        os.utime(resultado["arquivo_json"], (antigo, antigo))
        with self.assertRaisesRegex(ValueError, "esta antigo"):
            simular_fechamento(self.configuracao, resultado, input_fn=lambda _: "SIMULAR 1 OSS")

    def _criar_resultado(self, registros):
        id_execucao = "simulacao-teste"
        gerado_em = datetime.now()
        dados = {
            "registros": registros,
            "_meta_execucao": {
                "id_execucao": id_execucao,
                "gerado_em": gerado_em.isoformat(timespec="seconds"),
            },
        }
        Path(self.configuracao["arquivo_json_busca"]).write_text(json.dumps(dados), encoding="utf-8")
        Path(self.configuracao["relatorio_csv"]).write_text(
            "id,status,setor,data_abertura\n", encoding="utf-8"
        )
        return {
            "registros": registros,
            "arquivo_json": self.configuracao["arquivo_json_busca"],
            "relatorio_csv": self.configuracao["relatorio_csv"],
            "id_execucao": id_execucao,
            "gerado_em": gerado_em,
        }

    def _os(self, id_os, status="A", setor="9"):
        return {
            "id": id_os,
            "status": status,
            "setor": setor,
            "data_abertura": "2026-04-30 10:00:00",
        }

    def _contar_linhas(self, nome):
        with open(self.pasta / nome, "r", encoding="utf-8-sig", newline="") as arquivo:
            return sum(1 for _ in csv.DictReader(arquivo))


if __name__ == "__main__":
    unittest.main()
