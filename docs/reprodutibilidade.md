# Reprodutibilidade

Este documento existe para responder a uma pergunta específica: **dado um
número que aparece na dissertação, qual comando o produz?** Sem essa
correspondência, o repositório é um conjunto de scripts, e não um artefato de
verificação.

## Ambiente

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp configs/config.example.yaml configs/config.yaml
```

Versões fixadas em `requirements.txt`. Uma mudança de versão do `librosa` ou do
`scikit-learn` altera resultados numéricos **sem gerar erro**, e é esse tipo de
divergência silenciosa que inviabiliza a replicação anos depois.

A semente aleatória é fixada em `configs/config.yaml` (`projeto.seed`) e
propagada à Floresta Aleatória. Os demais métodos são determinísticos dadas as
mesmas partições.

## Cadeia completa

```bash
bash scripts/run_pipeline.sh              # dados reais em data/raw/
bash scripts/run_pipeline.sh --exemplo    # gera dados sintéticos antes
```

Ou passo a passo:

```bash
python -m noisedc.preprocessing.run --config configs/config.yaml
python -m noisedc.models.train --config configs/config.yaml
python -m noisedc.evaluation.run --protocol todos
python -m noisedc.viz.build_figures
```

## Correspondência com a dissertação

| Elemento | Comando | Artefato gerado |
|---|---|---|
| Composição do conjunto por unidade e estado | `python -m noisedc.preprocessing.run` | `data/processed/metadados_processados.csv` |
| Representações de um segmento (STFT, Mel, MFCC) | `python -m noisedc.preprocessing.run` (sem `--sem-imagens`) | `data/processed/<UNIDADE>/<gravacao>/{stft,mel}/` |
| Separabilidade intra-distribuição | `python -m noisedc.evaluation.run --protocol leave-one-recording-out` | `results/metrics/comparativo_metodos.csv` |
| Desempenho sob validação por unidade | `python -m noisedc.evaluation.run --protocol leave-one-unit-out` | `results/metrics/comparativo_metodos.csv` |
| Métricas por unidade anômala | mesmo comando | `results/metrics/metricas_por_particao.csv` |
| Matrizes de confusão | mesmo comando | `results/metrics/matriz_confusao__*.csv` |
| Decisão em nível de gravação | mesmo comando | `results/metrics/metricas_por_gravacao.csv` |
| Importância dos coeficientes MFCC | `python -m noisedc.models.train --metodo floresta_aleatoria` | `results/models/floresta_aleatoria.json` |
| Limiar ajustado do baseline | `python -m noisedc.models.train --metodo baseline` | `results/models/baseline.json` |
| Figuras de comparação e por unidade | `python -m noisedc.viz.build_figures` | `results/figures/` |

## Como ler os dois protocolos

`leave-one-recording-out` mede **separabilidade dentro da distribuição**: o
modelo distingue normal de anômalo no mesmo equipamento e nas mesmas condições?

`leave-one-unit-out` mede **generalização entre equipamentos**: o que foi
aprendido em algumas unidades vale para uma unidade nunca vista?

O segundo é sempre mais difícil, e **a diferença entre os dois é o resultado
interessante** — não o valor de nenhum deles isoladamente.

Particionar por segmento produziria números altos e sem significado: com 50% de
sobreposição, segmentos vizinhos compartilham metade do sinal, de modo que
treino e teste conteriam literalmente o mesmo áudio.

## Duas leituras das métricas

Cada avaliação produz números **por partição** e **agregados**:

- *por partição* (`metricas_por_particao.csv`) — mostra a dispersão entre
  unidades, que é o que responde à pergunta sobre generalização. Sob
  `leave-one-recording-out`, dobras de classe única têm AUC indefinida e
  aparecem como `NaN`, o que é esperado: toda gravação é inteiramente normal ou
  inteiramente anômala;
- *agregado* (`comparativo_metodos.csv`) — reúne as predições de todas as dobras
  antes de calcular as métricas. É o número comparável entre protocolos e o que
  corresponde à matriz de confusão reportada.

A média simples entre dobras seria enganosa quando algumas contêm poucos
segmentos anômalos: uma dobra com dois segmentos pesaria tanto quanto uma com
duzentos.

## Sobre a acurácia agregada

Ela é reportada, mas não é o critério de comparação. Com 1.749 segmentos
normais para 290 anômalos, um classificador que sempre responde "normal" atinge
cerca de 86% de acurácia sem detectar uma única falha. Recall, F1, AUC e a taxa
de falsos positivos são as métricas que carregam informação neste problema.

## Verificação de integridade

```bash
sha256sum -c data/CHECKSUMS.sha256
```

## Divergências esperadas

Pequenas diferenças nos decimais podem decorrer de versão de biblioteca,
arquitetura de processador ou ordem de paralelização da Floresta Aleatória.
Diferenças grandes indicam que algum parâmetro não foi registrado em
`configs/params.yaml` — nesse caso, o problema é do registro, não da execução.

## Testes

```bash
pytest -q                    # suíte completa
pytest tests/test_pipeline_e2e.py -q   # apenas a cadeia Camada 2 → 3 → 4
```

Os testes usam áudio sintético gerado em tempo de execução, e não amostras do
conjunto real: o repositório não precisa carregar arquivos de áudio para ser
testável, e o comportamento esperado fica explícito — sabemos exatamente qual
componente espectral foi inserida em cada sinal, então uma falha aponta para o
código, não para uma peculiaridade do dado.
