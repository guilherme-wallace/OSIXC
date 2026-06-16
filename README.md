# OSIXC

Projeto para apoiar a revisao e o fechamento em massa de OSs do IXC.

## Etapa atual: dry-run e relatorio

Nesta versao, o script apenas:

- busca OSs no IXC usando filtros configuraveis;
- salva o retorno bruto em JSON;
- valida a qualidade dos dados encontrados;
- gera um relatorio CSV para revisao;
- bloqueia qualquer acao destrutiva de fechamento, alteracao de setor ou registro de mensagem.

Nenhuma OS e fechada nesta etapa.

## Configuracao

Edite `config/busca_os_config.json` para ajustar:

- `setores_permitidos`: setores que podem entrar na busca;
- `status_finalizado`: status bloqueado/finalizado;
- `data_abertura_limite`: data maxima de abertura para a busca;
- `tecnico_responsavel`: tecnico que sera usado em etapa futura;
- `limite_por_lote`: quantidade maxima de OSs por execucao;
- `dry_run`: deve permanecer `true` nesta etapa;
- `arquivo_json_busca`: caminho do JSON de retorno;
- `relatorio_csv`: caminho do CSV de revisao;
- `validade_json_minutos`: tempo maximo para considerar o JSON recente.

## Como executar em dry-run

```bash
python main.py
```

Depois da execucao, revise o arquivo configurado em `relatorio_csv`.

## Como validar o CSV

Confira se todas as linhas respeitam:

- setor `9` ou `5`;
- status diferente de `F`;
- data de abertura menor que `2026-05-01 00:00:00`;
- campos importantes preenchidos, como `id`, `id_cliente`, `id_assunto` e `protocolo`;
- coluna `inconsistencias` vazia para os registros prontos para etapa futura.

## Proxima etapa sugerida

Somente depois de validar o CSV, implementar fechamento seguro com confirmacao, revalidacao antes da alteracao, relatorio de sucesso/falha e tratamento de erros repetidos.
