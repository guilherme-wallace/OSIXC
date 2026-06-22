import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from public.fechamento_cascata import (
    executar_cascata_real,
    executar_cascata_simulada,
)
from public.ixc_client import IXCAPIError
from public.travas_seguranca import _AutorizacaoFechamento


class FechamentoCascataTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.pasta = Path(self.temp_dir.name)
        self.configuracao = {
            "dry_run": True,
            "simulacao_fechamento": True,
            "fechamento_cascata_ativo": True,
            "frase_marcadora_fechamento": (
                "OS finalizada em lote via script de fechamento."
            ),
            "status_finalizado": "F",
            "max_rodadas_cascata": 5,
            "limite_por_rodada_cascata": 100,
            "intervalo_segundos_entre_rodadas": 0,
            "diretorio_relatorios_cascata": str(self.pasta),
            "limite_erros_repetidos": 3,
            "timeout_api_segundos": 5,
            "mensagem_fechamento": (
                "OS finalizada em lote via script de fechamento."
            ),
            "tecnico_responsavel": "96",
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cascata_nao_roda_por_padrao(self):
        self.configuracao["fechamento_cascata_ativo"] = False
        listar = Mock()

        resumo = executar_cascata_simulada(
            self.configuracao,
            listar_fn=listar,
            sleep_fn=lambda _: None,
        )

        self.assertFalse(resumo["ativo"])
        listar.assert_not_called()

    def test_cascata_simulada_exige_flag_e_modos_ativos(self):
        self.configuracao["dry_run"] = False

        with self.assertRaisesRegex(RuntimeError, "dry_run e simulacao ativos"):
            executar_cascata_simulada(self.configuracao)

    def test_para_quando_nao_encontra_mais_os(self):
        listar = Mock(side_effect=[[self._os("1")], []])
        obter = Mock(return_value=self._os("1"))

        resumo = executar_cascata_simulada(
            self.configuracao,
            listar_fn=listar,
            obter_fn=obter,
            sleep_fn=lambda _: None,
        )

        self.assertEqual(resumo["rodadas_executadas"], 2)
        self.assertEqual(resumo["total_fechado_ou_simulado"], 1)
        self.assertEqual(resumo["motivo_parada"], "nenhuma_os_marcada")

    def test_respeita_maximo_de_rodadas(self):
        self.configuracao["max_rodadas_cascata"] = 2
        listar = Mock(
            side_effect=[
                [self._os("1")],
                [self._os("2")],
            ]
        )
        obter = Mock(side_effect=[self._os("1"), self._os("2")])

        resumo = executar_cascata_simulada(
            self.configuracao,
            listar_fn=listar,
            obter_fn=obter,
            sleep_fn=lambda _: None,
        )

        self.assertEqual(resumo["rodadas_executadas"], 2)
        self.assertEqual(resumo["total_fechado_ou_simulado"], 2)
        self.assertEqual(resumo["motivo_parada"], "max_rodadas")

    def test_nao_processa_os_sem_marcador_ou_finalizada(self):
        listar = Mock(
            return_value=[
                self._os("1", mensagem="outra mensagem"),
                self._os("2", status="F"),
            ]
        )
        obter = Mock()

        resumo = executar_cascata_simulada(
            self.configuracao,
            listar_fn=listar,
            obter_fn=obter,
            sleep_fn=lambda _: None,
        )

        self.assertEqual(resumo["total_fechado_ou_simulado"], 0)
        self.assertEqual(resumo["total_ignorado"], 2)
        obter.assert_not_called()

    def test_simulacao_revalida_gera_relatorio_e_nao_envia_post(self):
        listar = Mock(side_effect=[[self._os("1")], []])
        obter = Mock(return_value=self._os("1"))

        with patch("public.ixc_client._requisicao_json") as requisicao:
            resumo = executar_cascata_simulada(
                self.configuracao,
                listar_fn=listar,
                obter_fn=obter,
                sleep_fn=lambda _: None,
            )

        requisicao.assert_not_called()
        obter.assert_called_once_with("1", 5)
        self.assertEqual(len(resumo["relatorios"]), 2)
        with open(
            resumo["relatorios"][0],
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as arquivo:
            linhas = list(csv.DictReader(arquivo))
        self.assertEqual(linhas[0]["resultado"], "SERIA_FECHADA")

    def test_ids_repetidos_bloqueiam_loop_infinito(self):
        self.configuracao["max_rodadas_cascata"] = 50
        listar = Mock(return_value=[self._os("1")])
        obter = Mock(return_value=self._os("1"))

        resumo = executar_cascata_simulada(
            self.configuracao,
            listar_fn=listar,
            obter_fn=obter,
            sleep_fn=lambda _: None,
        )

        self.assertEqual(resumo["rodadas_executadas"], 2)
        self.assertEqual(resumo["motivo_parada"], "sem_novos_ids_elegiveis")
        obter.assert_called_once()

    def test_cascata_real_exige_dry_run_false_e_capability(self):
        autorizacao = _AutorizacaoFechamento(
            "teste",
            [],
            cascata_permitida=True,
        )
        listar = Mock(side_effect=[[self._os("1")], []])
        obter = Mock(return_value=self._os("1"))
        fechar = Mock(return_value={"resposta": "ok"})

        with self.assertRaisesRegex(RuntimeError, "dry_run=false"):
            executar_cascata_real(
                self.configuracao,
                autorizacao,
                listar_fn=listar,
                obter_fn=obter,
                fechar_fn=fechar,
                sleep_fn=lambda _: None,
            )

        self.configuracao["dry_run"] = False
        resumo = executar_cascata_real(
            self.configuracao,
            autorizacao,
            listar_fn=listar,
            obter_fn=obter,
            fechar_fn=fechar,
            sleep_fn=lambda _: None,
        )

        self.assertEqual(resumo["total_fechado_ou_simulado"], 1)
        fechar.assert_called_once()
        self.assertIs(fechar.call_args.args[2], autorizacao)

    def test_erro_critico_para_sem_perguntar(self):
        listar = Mock(return_value=[self._os("1")])
        obter = Mock(
            side_effect=IXCAPIError(
                "resposta insegura",
                categoria="revalidacao",
                critico=True,
            )
        )
        input_fn = Mock()

        resumo = executar_cascata_simulada(
            self.configuracao,
            input_fn=input_fn,
            listar_fn=listar,
            obter_fn=obter,
            sleep_fn=lambda _: None,
        )

        self.assertEqual(resumo["motivo_parada"], "erro_critico")
        self.assertEqual(resumo["total_erros"], 1)
        input_fn.assert_not_called()

    def _os(self, id_os, status="A", mensagem=None):
        return {
            "id": id_os,
            "status": status,
            "mensagem": mensagem
            if mensagem is not None
            else self.configuracao["frase_marcadora_fechamento"],
        }


if __name__ == "__main__":
    unittest.main()
