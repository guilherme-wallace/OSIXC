import unittest
from unittest.mock import patch

from public.ixc_client import (
    IXCAPIError,
    fechar_os,
    listar_os_abertas_por_ticket,
    obter_os_por_id,
)


class IXCClientTests(unittest.TestCase):
    def setUp(self):
        self.configuracao = {
            "data_execucao": "22/06/2026",
            "mensagem_fechamento": "Teste seguro",
            "tecnico_responsavel": "96",
            "status_finalizado": "F",
            "timeout_api_segundos": 5,
        }

    def test_fechamento_monta_payload_esperado(self):
        with (
            patch("public.ixc_client.validar_e_consumir_autorizacao"),
            patch(
                "public.ixc_client._requisicao_json",
                return_value='{"type": "success"}',
            ) as requisicao,
        ):
            resultado = fechar_os("123", self.configuracao, object())

        payload = requisicao.call_args.kwargs["payload"]
        self.assertEqual(payload["id_chamado"], "123")
        self.assertEqual(payload["id_tecnico"], "96")
        self.assertEqual(payload["status"], "F")
        self.assertEqual(payload["data_inicio"], "22/06/2026")
        self.assertEqual(resultado["resposta"], '{"type": "success"}')

    def test_http_200_com_corpo_de_erro_nao_e_sucesso(self):
        with (
            patch("public.ixc_client.validar_e_consumir_autorizacao"),
            patch(
                "public.ixc_client._requisicao_json",
                return_value='{"type": "error", "message": "nao permitido"}',
            ),
        ):
            with self.assertRaisesRegex(IXCAPIError, "recusou"):
                fechar_os("123", self.configuracao, object())

    def test_chamada_direta_sem_capability_nao_envia_post(self):
        with patch("public.ixc_client._requisicao_json") as requisicao:
            with self.assertRaisesRegex(RuntimeError, "Capability"):
                fechar_os("123", self.configuracao)

        requisicao.assert_not_called()

    def test_capability_forjada_nao_envia_post(self):
        from public import travas_seguranca

        forjada = object.__new__(travas_seguranca._AutorizacaoFechamento)
        forjada._segredo = travas_seguranca._SEGREDO_CAPABILITY
        forjada.id_execucao = "forjada"
        forjada.ids_pendentes = {"123"}
        forjada.ids_ticket_autorizados = {"T-1"}
        forjada.cascata_permitida = True

        with patch("public.ixc_client._requisicao_json") as requisicao:
            with self.assertRaisesRegex(RuntimeError, "Capability"):
                fechar_os("123", self.configuracao, forjada)

        requisicao.assert_not_called()

    def test_revalidacao_rejeita_id_diferente(self):
        with patch(
            "public.ixc_client.listar_os",
            return_value={"registros": [{"id": "999"}]},
        ):
            with self.assertRaisesRegex(IXCAPIError, "retornou OS 999"):
                obter_os_por_id("123", 5)

    def test_listagem_por_ticket_usa_campo_id_ticket(self):
        configuracao = {
            "limite_por_rodada_cascata": 10,
            "status_finalizado": "F",
            "timeout_api_segundos": 5,
        }
        with patch(
            "public.ixc_client.listar_os",
            return_value={"registros": []},
        ) as listar:
            listar_os_abertas_por_ticket("T-1", configuracao)

        payload = listar.call_args.args[0]
        filtros = __import__("json").loads(payload["grid_param"])
        self.assertTrue(
            any(
                filtro["TB"] == "id_ticket"
                and filtro["OP"] == "="
                and filtro["P"] == "T-1"
                for filtro in filtros
            )
        )


if __name__ == "__main__":
    unittest.main()
