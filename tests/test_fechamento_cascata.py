import csv
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from public.fechamento_cascata import (
    executar_cascata_real,
    executar_cascata_simulada,
)
from public.simular_fechamento import simular_fechamento
from public.travas_seguranca import autorizar_fechamento


class FechamentoCascataTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.pasta = Path(self.temp_dir.name)
        self.configuracao = {
            "setores_permitidos": ["9", "5"],
            "status_finalizado": "F",
            "data_abertura_limite": "2026-05-01 00:00:00",
            "tecnico_responsavel": "96",
            "limite_por_lote": 10,
            "dry_run": True,
            "simulacao_fechamento": True,
            "fechamento_cascata_ativo": True,
            "max_rodadas_cascata": 5,
            "limite_por_rodada_cascata": 100,
            "intervalo_segundos_entre_rodadas": 0,
            "diretorio_relatorios_cascata": str(self.pasta / "cascata"),
            "limite_erros_repetidos": 3,
            "timeout_api_segundos": 5,
            "mensagem_fechamento": (
                "OS finalizada em lote via script de fechamento."
            ),
            "frase_marcadora_fechamento": (
                "OS finalizada em lote via script de fechamento."
            ),
            "arquivo_json_busca": str(self.pasta / "busca.json"),
            "relatorio_csv": str(self.pasta / "busca.csv"),
            "relatorio_sucessos_csv": str(self.pasta / "sucessos.csv"),
            "relatorio_erros_csv": str(self.pasta / "erros.csv"),
            "relatorio_simulacao_sucessos_csv": str(
                self.pasta / "simulacao_sucessos.csv"
            ),
            "relatorio_simulacao_erros_csv": str(
                self.pasta / "simulacao_erros.csv"
            ),
            "validade_json_minutos": 60,
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_coleta_id_ticket_das_os_iniciais(self):
        inicial = self._os("1", "T-1")
        resultado = self._resultado_busca([inicial])

        with patch(
            "public.simular_fechamento.executar_cascata_simulada"
        ) as cascata:
            cascata.return_value = {"ativo": True}
            simular_fechamento(
                self.configuracao,
                resultado,
                input_fn=lambda _: "SIMULAR 1 OSS",
                obter_os_fn=Mock(return_value=inicial),
            )

        self.assertEqual(cascata.call_args.args[1], {"T-1"})

    def test_fecha_os_criada_automaticamente_em_rodada_seguinte(self):
        listar = Mock(
            side_effect=[
                [self._os("10", "T-1")],
                [self._os("11", "T-1")],
                [],
            ]
        )
        obter = Mock(
            side_effect=[
                self._os("10", "T-1"),
                self._os("11", "T-1"),
            ]
        )

        resumo = executar_cascata_simulada(
            self.configuracao,
            {"T-1"},
            listar_fn=listar,
            obter_fn=obter,
            sleep_fn=lambda _: None,
        )

        self.assertEqual(resumo["total_fechado_ou_simulado"], 2)
        self.assertEqual(resumo["rodadas_executadas"], 3)
        self.assertEqual(
            resumo["motivo_parada"],
            "nenhuma_os_aberta_nos_atendimentos",
        )

    def test_bloqueia_os_de_ticket_nao_autorizado(self):
        listar = Mock(return_value=[self._os("10", "T-2")])
        obter = Mock()

        resumo = executar_cascata_simulada(
            self.configuracao,
            {"T-1"},
            listar_fn=listar,
            obter_fn=obter,
            sleep_fn=lambda _: None,
        )

        self.assertEqual(resumo["total_fechado_ou_simulado"], 0)
        self.assertEqual(resumo["total_ignorado"], 1)
        obter.assert_not_called()

    def test_bloqueia_status_finalizado(self):
        listar = Mock(return_value=[self._os("10", "T-1", status="F")])
        obter = Mock()

        resumo = executar_cascata_simulada(
            self.configuracao,
            {"T-1"},
            listar_fn=listar,
            obter_fn=obter,
            sleep_fn=lambda _: None,
        )

        self.assertEqual(resumo["total_fechado_ou_simulado"], 0)
        obter.assert_not_called()

    def test_bloqueia_loop_com_id_repetido(self):
        self.configuracao["max_rodadas_cascata"] = 50
        listar = Mock(return_value=[self._os("10", "T-1")])
        obter = Mock(return_value=self._os("10", "T-1"))

        resumo = executar_cascata_simulada(
            self.configuracao,
            {"T-1"},
            listar_fn=listar,
            obter_fn=obter,
            sleep_fn=lambda _: None,
        )

        self.assertEqual(resumo["rodadas_executadas"], 2)
        self.assertEqual(resumo["motivo_parada"], "sem_novos_ids_elegiveis")
        obter.assert_called_once()

    def test_simulacao_nao_envia_post_e_gera_csv_por_rodada(self):
        listar = Mock(side_effect=[[self._os("10", "T-1")], []])
        obter = Mock(return_value=self._os("10", "T-1"))

        with patch("public.ixc_client._requisicao_json") as requisicao:
            resumo = executar_cascata_simulada(
                self.configuracao,
                {"T-1"},
                listar_fn=listar,
                obter_fn=obter,
                sleep_fn=lambda _: None,
            )

        requisicao.assert_not_called()
        self.assertEqual(len(resumo["relatorios"]), 2)
        with open(
            resumo["relatorios"][0],
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as arquivo:
            linha = next(csv.DictReader(arquivo))
        self.assertEqual(linha["id_ticket"], "T-1")
        self.assertEqual(linha["resultado"], "SERIA_FECHADA")

    def test_execucao_real_mockada_com_multiplas_rodadas(self):
        self.configuracao["dry_run"] = False
        self.configuracao["simulacao_fechamento"] = False
        autorizacao = self._autorizacao_real("T-1")
        listar = Mock(
            side_effect=[
                [self._os("10", "T-1")],
                [self._os("11", "T-1")],
                [],
            ]
        )
        obter = Mock(
            side_effect=[
                self._os("10", "T-1"),
                self._os("11", "T-1"),
            ]
        )
        fechar = Mock(return_value={"resposta": "ok"})

        resumo = executar_cascata_real(
            self.configuracao,
            autorizacao,
            listar_fn=listar,
            obter_fn=obter,
            fechar_fn=fechar,
            sleep_fn=lambda _: None,
        )

        self.assertEqual(fechar.call_count, 2)
        self.assertEqual(resumo["total_fechado_ou_simulado"], 2)
        self.assertEqual(
            resumo["por_ticket"]["T-1"]["fechadas_ou_simuladas"],
            2,
        )

    def test_capability_forjada_nao_e_aceita(self):
        from public import travas_seguranca

        with self.assertRaisesRegex(RuntimeError, "fluxo confirmado"):
            travas_seguranca._AutorizacaoFechamento(
                object(),
                "forjada",
                [],
                {"T-1"},
                cascata_permitida=True,
            )

    def test_respeita_limite_por_rodada(self):
        self.configuracao["limite_por_rodada_cascata"] = 1
        listar = Mock(
            return_value=[
                self._os("10", "T-1"),
                self._os("11", "T-1"),
            ]
        )
        obter = Mock(return_value=self._os("10", "T-1"))

        resumo = executar_cascata_simulada(
            self.configuracao,
            {"T-1"},
            listar_fn=listar,
            obter_fn=obter,
            sleep_fn=lambda _: None,
        )

        self.assertEqual(resumo["total_fechado_ou_simulado"], 1)
        self.assertGreaterEqual(resumo["total_ignorado"], 1)

    def _autorizacao_real(self, id_ticket):
        resultado = self._resultado_busca([self._os("1", id_ticket)])
        return autorizar_fechamento(
            self.configuracao,
            resultado,
            ["1"],
            {id_ticket},
            input_fn=lambda _: "FECHAR 1 OSS",
        )

    def _resultado_busca(self, registros):
        id_execucao = "teste-cascata"
        gerado_em = datetime.now()
        dados = {
            "registros": registros,
            "_meta_execucao": {
                "id_execucao": id_execucao,
                "gerado_em": gerado_em.isoformat(timespec="seconds"),
            },
        }
        Path(self.configuracao["arquivo_json_busca"]).write_text(
            json.dumps(dados),
            encoding="utf-8",
        )
        Path(self.configuracao["relatorio_csv"]).write_text(
            "id,id_ticket,status\n",
            encoding="utf-8",
        )
        return {
            "registros": registros,
            "arquivo_json": self.configuracao["arquivo_json_busca"],
            "relatorio_csv": self.configuracao["relatorio_csv"],
            "id_execucao": id_execucao,
            "gerado_em": gerado_em,
        }

    def _os(self, id_os, id_ticket, status="A"):
        return {
            "id": id_os,
            "id_ticket": id_ticket,
            "status": status,
            "setor": "9",
            "data_abertura": "2026-04-30 10:00:00",
        }


if __name__ == "__main__":
    unittest.main()
