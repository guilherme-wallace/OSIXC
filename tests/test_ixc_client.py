import unittest
from unittest.mock import patch

from public.ixc_client import IXCAPIError, fechar_os


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
        with patch(
            "public.ixc_client._requisicao_json",
            return_value='{"type": "success"}',
        ) as requisicao:
            resultado = fechar_os("123", self.configuracao)

        payload = requisicao.call_args.kwargs["payload"]
        self.assertEqual(payload["id_chamado"], "123")
        self.assertEqual(payload["id_tecnico"], "96")
        self.assertEqual(payload["status"], "F")
        self.assertEqual(payload["data_inicio"], "22/06/2026")
        self.assertEqual(resultado["resposta"], '{"type": "success"}')

    def test_http_200_com_corpo_de_erro_nao_e_sucesso(self):
        with patch(
            "public.ixc_client._requisicao_json",
            return_value='{"type": "error", "message": "nao permitido"}',
        ):
            with self.assertRaisesRegex(IXCAPIError, "recusou"):
                fechar_os("123", self.configuracao)


if __name__ == "__main__":
    unittest.main()
