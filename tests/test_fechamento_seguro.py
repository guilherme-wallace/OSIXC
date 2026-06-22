import csv
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

from public.finalizar_OS import finalizar_OS
from public.ixc_client import IXCAPIError


class FechamentoSeguroTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.pasta = Path(self.temp_dir.name)
        self.configuracao = {
            "setores_permitidos": ["9", "5"],
            "status_finalizado": "F",
            "data_abertura_limite": "2026-05-01 00:00:00",
            "tecnico_responsavel": "96",
            "limite_por_lote": 100,
            "dry_run": False,
            "arquivo_json_busca": str(self.pasta / "busca.json"),
            "relatorio_csv": str(self.pasta / "busca.csv"),
            "relatorio_sucessos_csv": str(self.pasta / "sucessos.csv"),
            "relatorio_erros_csv": str(self.pasta / "erros.csv"),
            "validade_json_minutos": 60,
            "limite_erros_repetidos": 3,
            "mensagem_fechamento": "Fechamento seguro de teste",
            "timeout_api_segundos": 5,
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_dry_run_bloqueia_fechamento(self):
        resultado = self._criar_resultado([self._os("1")])
        self.configuracao["dry_run"] = True

        with self.assertRaisesRegex(RuntimeError, "dry_run=false"):
            finalizar_OS(self.configuracao, resultado)

    def test_confirmacao_invalida_nao_chama_ixc(self):
        resultado = self._criar_resultado([self._os("1")])
        obter = Mock()
        fechar = Mock()

        with self.assertRaisesRegex(RuntimeError, "Confirmacao invalida"):
            finalizar_OS(
                self.configuracao,
                resultado,
                input_fn=lambda _: "NAO CONFIRMO",
                obter_os_fn=obter,
                fechar_os_fn=fechar,
            )

        obter.assert_not_called()
        fechar.assert_not_called()

    def test_revalida_e_separa_sucesso_de_erro(self):
        resultado = self._criar_resultado([self._os("1"), self._os("2")])
        os_finalizada = self._os("2", status="F")
        obter = Mock(side_effect=[self._os("1"), os_finalizada])
        fechar = Mock(return_value={"resposta": '{"success": true}'})

        resumo = finalizar_OS(
            self.configuracao,
            resultado,
            input_fn=lambda _: "FECHAR 2 OSS",
            obter_os_fn=obter,
            fechar_os_fn=fechar,
        )

        self.assertEqual(resumo["total_sucessos"], 1)
        self.assertEqual(resumo["total_erros"], 1)
        fechar.assert_called_once()
        self.assertEqual(fechar.call_args.args[0], "1")
        self.assertIsNotNone(fechar.call_args.args[2])
        self.assertEqual(self._contar_linhas("sucessos.csv"), 1)
        self.assertEqual(self._contar_linhas("erros.csv"), 1)

    def test_erro_comum_continua_processamento(self):
        resultado = self._criar_resultado([self._os("1"), self._os("2")])
        obter = Mock(side_effect=[self._os("1"), self._os("2")])
        fechar = Mock(
            side_effect=[
                IXCAPIError("erro temporario", codigo_http=500, categoria="http"),
                {"resposta": "ok"},
            ]
        )

        resumo = finalizar_OS(
            self.configuracao,
            resultado,
            input_fn=lambda _: "FECHAR 2 OSS",
            obter_os_fn=obter,
            fechar_os_fn=fechar,
        )

        self.assertEqual(resumo["total_sucessos"], 1)
        self.assertEqual(resumo["total_erros"], 1)
        self.assertFalse(resumo["interrompido"])

    def test_erro_repetido_pergunta_e_pode_parar(self):
        self.configuracao["limite_erros_repetidos"] = 2
        resultado = self._criar_resultado(
            [self._os("1"), self._os("2"), self._os("3")]
        )
        obter = Mock(side_effect=[self._os("1"), self._os("2"), self._os("3")])
        fechar = Mock(
            side_effect=IXCAPIError("sem conexao", categoria="conexao")
        )
        respostas = iter(["FECHAR 3 OSS", "p"])

        resumo = finalizar_OS(
            self.configuracao,
            resultado,
            input_fn=lambda _: next(respostas),
            obter_os_fn=obter,
            fechar_os_fn=fechar,
        )

        self.assertTrue(resumo["interrompido"])
        self.assertEqual(resumo["total_erros"], 2)
        self.assertEqual(fechar.call_count, 2)

    def test_rejeita_json_de_outra_execucao(self):
        resultado = self._criar_resultado([self._os("1")])
        with open(resultado["arquivo_json"], "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        dados["_meta_execucao"]["id_execucao"] = "outra-execucao"
        with open(resultado["arquivo_json"], "w", encoding="utf-8") as arquivo:
            json.dump(dados, arquivo)

        with self.assertRaisesRegex(RuntimeError, "nao corresponde"):
            finalizar_OS(self.configuracao, resultado)

    def test_respeita_limite_por_lote(self):
        self.configuracao["limite_por_lote"] = 1
        resultado = self._criar_resultado([self._os("1"), self._os("2")])

        with self.assertRaisesRegex(RuntimeError, "excede limite_por_lote"):
            finalizar_OS(self.configuracao, resultado)

    def test_rejeita_json_antigo(self):
        resultado = self._criar_resultado([self._os("1")])
        instante_antigo = (
            datetime.now() - timedelta(hours=2)
        ).timestamp()
        os.utime(resultado["arquivo_json"], (instante_antigo, instante_antigo))

        with self.assertRaisesRegex(ValueError, "esta antigo"):
            finalizar_OS(self.configuracao, resultado)

    def test_id_duplicado_nao_e_fechado_duas_vezes(self):
        resultado = self._criar_resultado([self._os("1"), self._os("1")])
        obter = Mock(return_value=self._os("1"))
        fechar = Mock(return_value={"resposta": "ok"})

        resumo = finalizar_OS(
            self.configuracao,
            resultado,
            input_fn=lambda _: "FECHAR 1 OSS",
            obter_os_fn=obter,
            fechar_os_fn=fechar,
        )

        self.assertEqual(resumo["total_sucessos"], 1)
        self.assertEqual(resumo["total_erros"], 1)
        fechar.assert_called_once()

    def _criar_resultado(self, registros):
        id_execucao = "execucao-teste"
        gerado_em = datetime.now()
        dados = {
            "registros": registros,
            "_meta_execucao": {
                "id_execucao": id_execucao,
                "gerado_em": gerado_em.isoformat(timespec="seconds"),
            },
        }
        with open(self.configuracao["arquivo_json_busca"], "w", encoding="utf-8") as arquivo:
            json.dump(dados, arquivo)
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
            "id_cliente": "10",
            "id_assunto": "20",
            "protocolo": f"P-{id_os}",
        }

    def _contar_linhas(self, nome):
        with open(self.pasta / nome, "r", encoding="utf-8-sig", newline="") as arquivo:
            return sum(1 for _ in csv.DictReader(arquivo))


if __name__ == "__main__":
    unittest.main()
