# OSIXC

Projeto para buscar, revisar e fechar OSs do IXC em lote com travas de seguranca.

## Fluxo atual

Toda execucao comeca por uma busca nova no IXC:

1. Carrega `config/busca_os_config.json`.
2. Busca as OSs com os filtros configurados.
3. Gera um JSON com identificador unico da execucao.
4. Gera o CSV para revisao.
5. Se `dry_run=true`, encerra sem fechar nenhuma OS.
6. Se `dry_run=false`, valida todas as travas antes de iniciar o fechamento.
7. Reconsulta cada OS no IXC imediatamente antes de fecha-la.
8. Gera CSV separado de sucessos e erros.

O script nunca usa um JSON antigo para iniciar fechamento. A execucao real usa somente
o resultado criado pela busca feita no mesmo processo.

## Filtros

Os filtros padrao estao em `config/busca_os_config.json`:

- setores permitidos: `9` MANUTENCAO e `5` INSTALACAO;
- status diferente de `F`;
- data de abertura menor que `2026-05-01 00:00:00`;
- tecnico responsavel: `96`;
- limite por lote configuravel;
- `dry_run=true` por padrao.

## Arquivos gerados

- `src/pegaOSResultado.json`: retorno da busca e identificador da execucao;
- `src/relatorio_os_encontradas.csv`: OSs encontradas e inconsistencias;
- `src/relatorio_fechamentos_sucesso.csv`: fechamentos confirmados pelo endpoint;
- `src/relatorio_fechamentos_erro.csv`: falhas, mudancas de filtro e OSs ignoradas.

## Teste em dry-run

Mantenha:

```json
"dry_run": true
```

Execute:

```powershell
python main.py
```

O script faz a busca e gera o CSV, mas nao acessa o endpoint de fechamento.

Revise se:

- todas as OSs pertencem aos setores `9` ou `5`;
- nenhuma OS tem status `F`;
- todas foram abertas antes da data limite;
- a quantidade esta dentro de `limite_por_lote`;
- a coluna `inconsistencias` foi avaliada.

## Execucao real segura

Antes da execucao:

1. Confirme os filtros e o limite no arquivo de configuracao.
2. Altere conscientemente `dry_run` para `false`.
3. Execute `python main.py`.
4. Aguarde a nova busca e confira o total mostrado.
5. Digite exatamente a frase solicitada, por exemplo `FECHAR 25 OSS`.

Sem a frase exata, nenhuma OS e fechada.

Para cada OS, o script reconsulta o IXC e valida novamente setor, status e data de
abertura. Se a OS mudou desde a busca, ela vai para o CSV de erros e nao e fechada.

O payload usa o tecnico configurado, status `F`, a mensagem configurada e a data da
execucao como `data_inicio` e `data_final`.

Depois da execucao, retorne `dry_run` para `true` e revise os dois CSVs de resultado.

## Tratamento de erros

- Erro comum: registra no CSV e continua.
- Erro critico, como autenticacao: pergunta se deve continuar, ignorar o tipo ou parar.
- Erro repetido: ao atingir `limite_erros_repetidos`, faz a mesma pergunta.
- Entrada invalida durante situacao critica pede uma nova opcao; encerramento da
  entrada (EOF) usa a opcao segura de parar.

## Testes automatizados

```powershell
python -m unittest discover -s tests -v
```

Os testes usam mocks e arquivos temporarios. Eles nao fazem chamadas reais ao IXC.

## Configuracoes principais

- `limite_por_lote`: quantidade maxima recebida pela execucao;
- `validade_json_minutos`: validade maxima dos artefatos;
- `limite_erros_repetidos`: quantidade antes da pergunta interativa;
- `mensagem_fechamento`: mensagem enviada ao IXC;
- `timeout_api_segundos`: timeout das chamadas;
- `relatorio_sucessos_csv` e `relatorio_erros_csv`: caminhos dos resultados.

As rotinas antigas de fechamento por mensagem, mudanca de setor e registro de mensagem
continuam bloqueadas. O unico caminho autorizado e o fluxo seguro de `main.py`.
