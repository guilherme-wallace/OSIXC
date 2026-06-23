import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import main
from public.modo_emergencial import (
    buscar_os_emergenciais,
    executar_modo_emergencial,
)


class ModoEmergencialTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.pasta = Path(self.temp_dir.name)
        self.frase = "OS finalizada em lote via script de fechamento."
        self.configuracao = {
            "modo_emergencial_por_mensagem": True,
            "mensagem_busca_emergencial": self.frase,
            "status_finalizado": "F",
            "tecnico_responsavel": "96",
            "limite_por_lote": 10,
            "dry_run": True,
            "validade_json_minutos": 60,
            "timeout_api_segundos": 5,
            "mensagem_fechamento": self.frase,
            "fechamento_cascata_ativo": False,
            "arquivo_json_emergencial": str(self.pasta / "busca.json"),
            "relatorio_emergencial_csv": str(self.pasta / "revisao.csv"),
            "relatorio_emergencial_sucessos_csv": str(
                self.pasta / "sucessos.csv"
            ),
            "relatorio_emergencial_erros_csv": str(self.pasta / "erros.csv"),
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_busca_por_mensagem_gera_json_e_csv(self):
        listar = Mock(return_value={"registros": [self._os("1")]})

        resultado = buscar_os_emergenciais(
            self.configuracao,
            listar_fn=listar,
        )

        payload = listar.call_args.args[0]
        filtros = json.loads(payload["grid_param"])
        self.assertTrue(
            any(
                filtro["TB"] == "mensagem"
                and filtro["OP"] == "LIKE"
                and filtro["P"] == self.frase
                for filtro in filtros
            )
        )
        self.assertTrue(
            any(
                filtro["TB"] == "status"
                and filtro["OP"] == "!="
                and filtro["P"] == "F"
                for filtro in filtros
            )
        )
        self.assertEqual(payload["rp"], "11")
        self.assertEqual(resultado["total_encontrado"], 1)
        self.assertTrue(Path(resultado["arquivo_json"]).exists())
        self.assertEqual(self._contar_linhas("revisao.csv"), 1)

    def test_dry_run_nao_envia_post(self):
        with patch("public.ixc_client._requisicao_json") as requisicao:
            resumo = executar_modo_emergencial(
                self.configuracao,
                listar_fn=Mock(return_value={"registros": [self._os("1")]}),
            )

        requisicao.assert_not_called()
        self.assertEqual(resumo["total_elegiveis"], 1)
        self.assertEqual(resumo["total_sucessos"], 0)
        self.assertEqual(self._contar_linhas("sucessos.csv"), 0)

    def test_main_emergencial_nao_executa_busca_normal(self):
        resumo = {
            "total_encontrado": 1,
            "total_elegiveis": 1,
            "total_sucessos": 0,
            "total_erros": 0,
        }
        with (
            patch(
                "main.carregar_configuracao",
                return_value={"modo_emergencial_por_mensagem": True},
            ),
            patch(
                "main.executar_modo_emergencial",
                return_value=resumo,
            ) as emergencial,
            patch("main.obter_dados_OS") as busca_normal,
            patch("main.finalizar_OS") as finalizar,
        ):
            main.main()

        emergencial.assert_called_once()
        busca_normal.assert_not_called()
        finalizar.assert_not_called()

    def test_fechamento_real_exige_confirmacao(self):
        self.configuracao["dry_run"] = False
        obter = Mock()
        fechar = Mock()

        with self.assertRaisesRegex(RuntimeError, "Confirmacao invalida"):
            executar_modo_emergencial(
                self.configuracao,
                input_fn=lambda _: "NAO",
                listar_fn=Mock(return_value={"registros": [self._os("1")]}),
                obter_fn=obter,
                fechar_fn=fechar,
            )

        obter.assert_not_called()
        fechar.assert_not_called()

    def test_revalidacao_bloqueia_os_sem_frase(self):
        resumo, fechar = self._executar_real(
            atual=self._os("1", mensagem="outra mensagem")
        )

        self.assertEqual(resumo["total_sucessos"], 0)
        self.assertEqual(resumo["total_erros"], 1)
        fechar.assert_not_called()

    def test_revalidacao_bloqueia_status_finalizado(self):
        resumo, fechar = self._executar_real(atual=self._os("1", status="F"))

        self.assertEqual(resumo["total_sucessos"], 0)
        self.assertEqual(resumo["total_erros"], 1)
        fechar.assert_not_called()

    def test_revalidacao_bloqueia_id_diferente(self):
        resumo, fechar = self._executar_real(atual=self._os("999"))

        self.assertEqual(resumo["total_sucessos"], 0)
        self.assertEqual(resumo["total_erros"], 1)
        fechar.assert_not_called()

    def test_fechamento_real_gera_csv_sucesso_e_erro(self):
        self.configuracao["dry_run"] = False
        registros = [self._os("1"), self._os("2")]
        obter = Mock(
            side_effect=[
                self._os("1"),
                self._os("2", status="F"),
            ]
        )
        fechar = Mock(return_value={"resposta": "ok"})

        resumo = executar_modo_emergencial(
            self.configuracao,
            input_fn=lambda _: "FECHAR 2 OSS",
            listar_fn=Mock(return_value={"registros": registros}),
            obter_fn=obter,
            fechar_fn=fechar,
        )

        self.assertEqual(resumo["total_sucessos"], 1)
        self.assertEqual(resumo["total_erros"], 1)
        self.assertEqual(self._contar_linhas("sucessos.csv"), 1)
        self.assertEqual(self._contar_linhas("erros.csv"), 1)

    def _executar_real(self, atual):
        self.configuracao["dry_run"] = False
        fechar = Mock(return_value={"resposta": "ok"})
        resumo = executar_modo_emergencial(
            self.configuracao,
            input_fn=lambda _: "FECHAR 1 OSS",
            listar_fn=Mock(return_value={"registros": [self._os("1")]}),
            obter_fn=Mock(return_value=atual),
            fechar_fn=fechar,
        )
        return resumo, fechar

    def _os(self, id_os, status="A", mensagem=None):
        return {
            "id": id_os,
            "id_ticket": "T-1",
            "id_cliente": "C-1",
            "setor": "99",
            "status": status,
            "data_abertura": "2026-06-20 10:00:00",
            "mensagem": self.frase if mensagem is None else mensagem,
        }

    def _contar_linhas(self, nome):
        with open(
            self.pasta / nome,
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as arquivo:
            return sum(1 for _ in csv.DictReader(arquivo))


if __name__ == "__main__":
    unittest.main()
