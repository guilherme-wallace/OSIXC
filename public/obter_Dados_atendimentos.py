import requests
import base64
import json
import os
from route.dadosDeconexao import hostIXC, tokenIXC

FRASE_MARCADORA = "OS finalizada em lote via script de fechamento."

def gerar_token_base64():
    token = tokenIXC

    if isinstance(token, str):
        token = token.encode("utf-8")

    return base64.b64encode(token).decode("utf-8")

def obter_dados_atendimentos(arquivo_saida_atendimentos_json):
    url = f"https://{hostIXC}/webservice/v1/su_mensagens"

    payload = {
        "qtype": "su_mensagens.mensagem",
        "query": FRASE_MARCADORA,
        "oper": "L",
        "page": "1",
        "rp": "10000",
        "sortname": "su_mensagens.id",
        "sortorder": "desc"
    }

    headers = {
        "ixcsoft": "listar",
        "Authorization": "Basic {}".format(gerar_token_base64()),
        "Content-Type": "application/json"
    }

    response = requests.get(
        url,
        data=json.dumps(payload),
        headers=headers
    )

    try:
        json_data = response.json()

        with open(arquivo_saida_atendimentos_json, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)

        print(f"Os dados foram salvos no arquivo JSON '{arquivo_saida_atendimentos_json}'.")

        registros = json_data.get("registros", [])

        print(f"Total retornado pela consulta: {json_data.get('total', 0)}")
        print(f"Registros salvos neste arquivo: {len(registros)}")

        if registros:
            caminho_pasta = os.path.dirname(arquivo_saida_atendimentos_json)
            arquivo_resumo = os.path.join(
                caminho_pasta,
                "mensagens_atendimentos_para_deletar.json"
            )

            mensagens_para_deletar = []

            for registro in registros:
                mensagem = registro.get("mensagem", "")

                if isinstance(mensagem, str) and FRASE_MARCADORA in mensagem:
                    mensagens_para_deletar.append({
                        "id_mensagem": registro.get("id", ""),
                        "id_ticket": registro.get("id_ticket", ""),
                        "data": registro.get("data", ""),
                        "operador": registro.get("operador", ""),
                        "mensagem": mensagem
                    })

            with open(arquivo_resumo, "w", encoding="utf-8") as f:
                json.dump(mensagens_para_deletar, f, ensure_ascii=False, indent=4)

            print(f"Arquivo resumido criado em '{arquivo_resumo}'.")
            print(f"Mensagens no resumo: {len(mensagens_para_deletar)}")

    except ValueError as e:
        print(f"Erro ao processar resposta como JSON: {e}")
        print(f"Resposta bruta: {response.text}")

if __name__ == "__main__":
    obter_dados_atendimentos("src/pegaAtendimentosResultado.json")