import requests
import base64
import json
import os
from route.dadosDeconexao import hostIntranet, urlIXC, tokenIXC

def obter_dados_OS(arquivo_saida_pega_OS_json):
    host = hostIntranet
    url = urlIXC.format(host)
    token = tokenIXC

    payload = {
        'qtype': 'su_oss_chamado.id',
        'query': '0',
        'oper': '>',
        'page': '1',
        'rp': '10000',
        'grid_param': json.dumps([
            {
                "TB": "status",
                "OP": "!=",
                "P": "F"
            },
            {
                "TB": "data_abertura",
                "OP": ">",
                "P": "2025-02-01 00:00:00"
            }
        ]),
        'sortname': 'su_oss_chamado.id',
        'sortorder': 'asc'
    }

    headers = {
        'ixcsoft': 'listar',
        'Authorization': 'Basic {}'.format(base64.b64encode(token).decode('utf-8')),
        'Content-Type': 'application/json'
    }

    response = requests.get(url, data=json.dumps(payload), headers=headers)
    
    try:
        json_data = response.json()
        
        with open(arquivo_saida_pega_OS_json, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)
        
        print(f"Os dados foram salvos no arquivo JSON '{arquivo_saida_pega_OS_json}'.")
        
        if 'registros' in json_data and len(json_data['registros']) > 0:
            caminho_pasta = os.path.dirname(arquivo_saida_pega_OS_json)
            novo_arquivo = os.path.join(caminho_pasta, 'tickets_finalizados.json')
            
            tickets_finalizados = []
            for registro in json_data['registros']:
                ticket = {
                    "id_ticket": registro.get('id', ''),
                    "mensagem": "OS finalizado via script",
                    "su_status": "S"
                }
                tickets_finalizados.append(ticket)
            
            with open(novo_arquivo, 'w', encoding='utf-8') as f:
                json.dump(tickets_finalizados, f, ensure_ascii=False, indent=4)
            
            print(f"Arquivo com tickets para finalização criado em '{novo_arquivo}'.")
            
    except ValueError as e:
        print(f"Erro ao processar a resposta como JSON: {e}")
        print(f"Resposta bruta: {response.text}")