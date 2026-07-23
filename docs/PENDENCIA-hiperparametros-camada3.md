# Verificação de hiperparâmetros da Camada 3 — RESOLVIDA

**Status: resolvida em 2026-07-23**, por comparação numérica direta entre a
saída de [`src/noisedc/legado/camada3_autoritativo_linha_c.py`](../src/noisedc/legado/camada3_autoritativo_linha_c.py)
executado sobre o `features_segmentos.csv` real (2.818 segmentos, 96
gravações) e as Tabelas 12, 13 e 14 do Capítulo 5 da dissertação.

## O que foi encontrado originalmente

A Tabela 9 (Seção 5.2, configuração dos métodos) reporta:

| Hiperparâmetro | Tabela 9 |
|---|---|
| SVM — `C` | 1,0 |
| Floresta Aleatória — nº de árvores | 100 |
| One-Class SVM — `ν` | 0,5 |

O script executado usa `C=10`, `n_estimators=400`, `ν=0,1` — valores
diferentes dos da Tabela 9.

## Verificação

A execução do script sobre os dados reais produziu, sob `leave-one-unit-out`
em nível de segmento:

| Método | Acur. | Prec. | Recall | F1 | AUC | FPR |
|---|---|---|---|---|---|---|
| Baseline (1 característica) | 0,655 | 0,000 | 0,000 | 0,000 | 0,428 | 0,236 |
| SVM (RBF) | 0,848 | 0,000 | 0,000 | 0,000 | 0,534 | 0,011 |
| Floresta Aleatória | 0,857 | 0,000 | 0,000 | 0,000 | 0,505 | 0,001 |
| One-Class SVM | 0,775 | 0,281 | 0,372 | 0,320 | 0,609 | 0,158 |

Esses valores **coincidem, casa a casa** (com diferença de ±0,001 no AUC da
SVM, atribuível à ausência de `random_state` fixo na calibração de
probabilidade interna do `SVC`) com a **Tabela 12** da dissertação. O mesmo
vale para a Tabela 13 (LORO: SVM AUC = 0,990/0,998; Floresta Aleatória =
0,986/1,000 — ambas exatas) e a Tabela 14 (decisão por gravação).

## Conclusão

**Os hiperparâmetros do script (`C=10`, `n_estimators=400`, `ν=0,1`) são os
que efetivamente produziram os resultados publicados no Capítulo 5.** A
Tabela 9 não reflete a configuração final — é, provavelmente, um resquício de
uma versão anterior do texto que não foi atualizada quando os hiperparâmetros
foram ajustados.

**Ação recomendada:** levar esta divergência ao orientador. Trata-se de uma
errata na Tabela 9 da dissertação já depositada (Seção 5.2), não um problema
no código nem nos resultados em si — as Tabelas 12, 13 e 14 (que reportam os
números finais) estão corretas e reprodutíveis.

## Observação secundária: pequena variação não determinística

A SVM apresenta diferença de ±0,005 em AUC entre execuções (0,533–0,534 no
nível de segmento; 0,442–0,447 no nível de gravação), porque
`SVC(..., probability=True)` executa uma validação cruzada interna de Platt
sem `random_state` fixo. Não afeta nenhuma conclusão qualitativa, mas quem for
reexecutar o script deve esperar variação na terceira casa decimal do AUC da
SVM especificamente — os demais métodos são deterministas.

## Convenção adotada nos arquivos de configuração deste repositório

`configs/params.yaml` foi atualizado para refletir os valores **confirmados
por esta verificação** (`C=10`, `n_estimators=400`, `ν=0,1`), com nota
explícita da divergência com a Tabela 9 do texto.
