# Dicionário de dados

## `data/raw/<UNIDADE>/metadados.csv`

Registro de coleta, preenchido pela Camada 1 no momento da transferência.

| Campo | Tipo | Descrição |
|---|---|---|
| `arquivo` | texto | nome do `.wav`, relativo à pasta da unidade |
| `equipamento` | texto | identificador da evaporadora (`EV09` a `EV14`) |
| `estado` | categórico | `normal`, `anomalia`, `standby` ou `referencia` |
| `sessao_coleta` | texto | identificador da sessão, no formato `AAAA-MM-DD_HHMM` |
| `referencia` | texto | arquivo de referência da sessão; vazio quando ausente |
| `coletado_em` | ISO 8601 | momento da transferência ao servidor |
| `observacoes` | texto livre | condições de coleta, intervenções em curso |

## `data/processed/metadados_processados.csv`

Uma linha por segmento, produzida pela Camada 2. É o índice que liga cada
artefato derivado ao arquivo bruto que o originou.

| Campo | Tipo | Descrição |
|---|---|---|
| `arquivo_origem` | texto | caminho do `.wav` de origem, relativo a `data/raw/` |
| `indice_segmento` | inteiro | posição do segmento dentro da gravação, a partir de 0 |
| `equipamento` | texto | unidade monitorada |
| `estado` | categórico | rótulo herdado da gravação |
| `sessao_coleta` | texto | sessão de coleta |
| `inicio_s` | decimal | início do segmento, em segundos a partir do começo da gravação |
| `usou_referencia` | 0 ou 1 | se a subtração espectral foi aplicada |
| `energia_banda` | decimal | energia espectral média na banda diagnóstica; entrada do baseline |
| `caminho_stft` | texto | espectrograma STFT (`.png`); vazio se gerado com `--sem-imagens` |
| `caminho_mel` | texto | espectrograma Mel (`.png`) |
| `caminho_mfcc` | texto | matriz MFCC + deltas (`.npy`), forma `(40, n_quadros)` |

A coluna `usou_referencia` merece atenção na análise: um conjunto em que parte
dos segmentos passou pela subtração espectral e parte não passou introduz uma
variação sistemática que o classificador pode aprender como se fosse
informação sobre o equipamento.

## Descritor de 60 dimensões

Vetor de entrada dos classificadores, derivado da matriz MFCC por agregação
temporal.

| Posições | Conteúdo |
|---|---|
| 0 a 19 | média de cada um dos 20 coeficientes cepstrais |
| 20 a 39 | desvio-padrão de cada um dos 20 coeficientes |
| 40 a 59 | média de cada um dos 20 deltas |

Os rótulos correspondentes são obtidos por
`noisedc.features.descriptors.nomes_das_dimensoes()`, e servem aos gráficos de
importância de atributos da Floresta Aleatória.

O desvio-padrão dos deltas é omitido deliberadamente: mede a variação da
variação, é dominado por ruído em janelas de 2 s e acrescentaria 20 dimensões
sem acrescentar informação em um conjunto deste tamanho.

## Artefatos de resultado

| Arquivo | Conteúdo |
|---|---|
| `results/metrics/comparativo_metodos.csv` | métricas agregadas por método e protocolo |
| `results/metrics/metricas_por_particao.csv` | uma linha por dobra; mostra a dispersão entre unidades |
| `results/metrics/metricas_por_gravacao.csv` | decisão consolidada em nível de gravação |
| `results/metrics/matriz_confusao__<metodo>__<protocolo>.csv` | matriz de confusão acumulada |
| `results/models/<metodo>.joblib` | modelo treinado sobre todo o conjunto, para a Camada 4 |
| `results/models/<metodo>.json` | ficha do treinamento: data, composição, semente, atributos mais importantes |

## Convenção de rótulos

Em todo o código: **0 = normal, 1 = anomalia**. Nos escores contínuos, **valores
maiores indicam maior evidência de anomalia** — inclusive no One-Class SVM, cuja
saída nativa do scikit-learn é invertida pelo adaptador para respeitar essa
convenção. É o que permite calcular AUC de forma uniforme entre os quatro
métodos.
