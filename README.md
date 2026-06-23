# OSIXC

Projeto para buscar, revisar e fechar OSs do IXC em lote com travas de seguranca.

## Modos de execucao

| Modo | `dry_run` | `simulacao_fechamento` | Comportamento |
| --- | --- | --- | --- |
| Dry-run | `true` | `false` | Busca e gera o CSV inicial. Nao revalida cada OS e nao fecha. |
| Simulacao | `true` | `true` | Executa travas, confirmacao e revalidacao completa, sem POST de fechamento. |
| Fechamento real | `false` | `false` | Revalida e fecha somente com capability valida. |

`dry_run=true` e `simulacao_fechamento=false` continuam sendo os valores padrao.

## Fluxo atual

Toda execucao comeca por uma busca nova no IXC:

1. Carrega `config/busca_os_config.json`.
2. Busca as OSs com os filtros configurados.
3. Gera um JSON com identificador unico da execucao.
4. Gera o CSV para revisao.
5. Escolhe dry-run, simulacao ou fechamento real.
6. Simulacao e fechamento real validam artefatos, limite e confirmacao.
7. Reconsulta cada OS imediatamente antes de simular ou fechar.
8. Gera CSVs separados para o modo executado.

O script nunca usa um JSON antigo para iniciar simulacao ou fechamento.

## Filtros

- setores permitidos: `9` MANUTENCAO e `5` INSTALACAO;
- status diferente de `F`;
- data de abertura menor que `2026-05-01 00:00:00`;
- tecnico responsavel: `96`;
- limite por lote configuravel.

## Arquivos gerados

- `src/pegaOSResultado.json`;
- `src/relatorio_os_encontradas.csv`;
- `src/relatorio_fechamentos_sucesso.csv`;
- `src/relatorio_fechamentos_erro.csv`;
- `src/relatorio_simulacao_sucessos.csv`;
- `src/relatorio_simulacao_erros.csv`;
- `src/relatorios_cascata/cascata_<modo>_<execucao>_rodada_<NN>.csv`.

## Dry-run

Configure:

```json
"dry_run": true,
"simulacao_fechamento": false
```

Execute `python main.py`. O script busca e gera o CSV inicial, sem revalidacao individual e sem fechamento.

## Simulacao completa

Configure:

```json
"dry_run": true,
"simulacao_fechamento": true
```

Execute `python main.py` e confirme exatamente `SIMULAR N OSS`. A simulacao valida JSON/CSV recentes, limite por lote e reconsulta cada OS. Ela nao cria capability e nao chama `fechar_os()`.

Revise no resumo e nos CSVs:

- total encontrado e dentro do lote;
- total que seria fechado;
- erros de revalidacao;
- registros ignorados;
- tempo aproximado.

Recomenda-se executar e revisar a simulacao antes de qualquer fechamento real.

## Fechamento real

Configure conscientemente:

```json
"dry_run": false,
"simulacao_fechamento": false
```

Execute `python main.py`, confira a busca nova e confirme exatamente `FECHAR N OSS`. Cada OS e reconsultada antes do POST e o fechamento exige capability valida.

Depois, retorne `dry_run` para `true` e revise os CSVs de sucesso e erro.

## Fechamento em cascata

A cascata coleta o campo `id_ticket` das OSs iniciais elegiveis e procura todas
as OSs abertas desses mesmos atendimentos. O JSON real do IXC retorna o campo
com o nome `id_ticket`, que tambem e usado no filtro da listagem.

Ela e desativada por padrao e nunca cria uma autorizacao propria. A capability
emitida depois da confirmacao guarda os atendimentos autorizados.

Configuracoes:

```json
"fechamento_cascata_ativo": false,
"frase_marcadora_fechamento": "OS finalizada em lote via script de fechamento.",
"max_rodadas_cascata": 5,
"limite_por_rodada_cascata": 100,
"intervalo_segundos_entre_rodadas": 5
```

Cada rodada espera o intervalo configurado, busca por `id_ticket`, revalida ID
da OS, status e atendimento, gera um CSV e mostra um resumo geral e por
atendimento. IDs ja processados nao podem ser fechados novamente. O fluxo para
quando nao ha novas OSs, quando atinge o maximo de rodadas, em erro critico, em
erro de busca ou quando o operador escolhe parar apos erros repetidos.

A frase marcadora continua em `mensagem_fechamento` e e enviada ao IXC, mas nao
e usada como filtro principal da cascata.

### Simular a cascata

Configure:

```json
"dry_run": true,
"simulacao_fechamento": true,
"fechamento_cascata_ativo": true
```

Execute `python main.py` e confirme `SIMULAR N OSS`. A busca inicial coleta os
atendimentos e a cascata simula todas as OSs abertas encontradas por `id_ticket`,
sem enviar POST de fechamento. Revise o resumo por atendimento e todos os CSVs
em `src/relatorios_cascata/`.

### Executar a cascata real

Primeiro valide a simulacao. Para um primeiro teste real, use:

```json
"dry_run": false,
"simulacao_fechamento": false,
"fechamento_cascata_ativo": true,
"limite_por_lote": 1,
"max_rodadas_cascata": 1,
"limite_por_rodada_cascata": 1
```

Confirme exatamente `FECHAR N OSS`. A cascata real somente inicia depois do
fechamento inicial autorizado e usa a mesma capability e os mesmos
`id_ticket`. Mantenha `mensagem_fechamento` contendo a frase marcadora. Ao
terminar, restaure `dry_run=true` e `fechamento_cascata_ativo=false`.

## Tratamento de erros reais

- Erro comum: registra e continua.
- Erro critico ou repetido: pergunta se deve continuar, ignorar o tipo ou parar.
- Entrada invalida pede nova opcao; EOF para com seguranca.

## Testes

```powershell
python -m unittest discover -s tests -v
```

Os testes usam mocks e arquivos temporarios. Nao fazem chamadas reais de fechamento.

## Configuracoes principais

- `limite_por_lote`;
- `simulacao_fechamento`;
- `validade_json_minutos`;
- `limite_erros_repetidos`;
- `mensagem_fechamento`;
- `timeout_api_segundos`;
- `fechamento_cascata_ativo`;
- `frase_marcadora_fechamento`;
- `max_rodadas_cascata`;
- `limite_por_rodada_cascata`;
- `intervalo_segundos_entre_rodadas`;
- caminhos dos relatorios reais e simulados.

As rotinas destrutivas antigas continuam bloqueadas. O unico caminho real autorizado e o fluxo seguro de `main.py`.

## Modo emergencial por mensagem

Este modo e independente dos filtros normais de setor e data. Ele deve ser
usado somente para localizar OSs abertas cuja mensagem contenha a frase
configurada.

Valores padrao:

```json
"modo_emergencial_por_mensagem": false,
"mensagem_busca_emergencial": "OS finalizada em lote via script de fechamento.",
"dry_run": true
```

Quando ativo, o `main.py` nao executa a busca normal. Ele:

1. busca somente `status != F` e `mensagem LIKE mensagem_busca_emergencial`;
2. gera JSON e CSV exclusivos para revisao;
3. bloqueia IDs duplicados e registros inconsistentes;
4. em dry-run, encerra sem POST;
5. em modo real, valida artefatos e limite, exige `FECHAR N OSS`, reconsulta
   cada OS e confirma novamente status e mensagem antes de fechar.

Relatorios:

- `src/relatorio_emergencial_revisao.csv`;
- `src/relatorio_emergencial_sucessos.csv`;
- `src/relatorio_emergencial_erros.csv`.

### Revisao emergencial em dry-run

```json
"modo_emergencial_por_mensagem": true,
"dry_run": true,
"limite_por_lote": 100
```

Execute `python main.py` e revise o CSV de revisao. Nenhuma OS e alterada.

### Execucao emergencial real limitada

Depois de validar o CSV:

```json
"modo_emergencial_por_mensagem": true,
"dry_run": false,
"limite_por_lote": 1
```

Execute `python main.py` e digite exatamente `FECHAR N OSS`. Ao terminar,
restaure `dry_run=true` e `modo_emergencial_por_mensagem=false`.
