# Protocolo de coleta

## Posicionamento

O protótipo é fixado a **5 cm da grade de saída de ar** da evaporadora, em
suporte que mantém constantes a distância, a altura e a orientação do microfone
em relação à unidade monitorada.

A constância importa mais que o valor exato: a relação sinal-ruído depende do
posicionamento, da distância às fontes e da geometria do corredor, de modo que
gravações feitas em posições diferentes não são comparáveis entre si, ainda que
normalizadas.

## Tipos de gravação

| Tipo | Condição | Uso |
|---|---|---|
| **Operacional** | unidade em funcionamento | material de análise |
| **Referência** | unidade desligada ou em silêncio | estimativa do ruído de fundo para a subtração espectral |

Toda sessão produz as duas. Uma gravação operacional sem a referência
correspondente pode ser processada, mas sem subtração espectral — e essa
diferença de tratamento fica registrada na coluna `usou_referencia` dos
metadados, porque um conjunto em que parte dos arquivos passou pela subtração e
parte não passou introduz uma variação que o classificador aprende como se
fosse informação sobre o equipamento.

## Estados registrados

| Estado | Descrição |
|---|---|
| `normal` | operação regular, sem indício de falha |
| `anomalia` | condição anômala confirmada por evidência externa |
| `standby` | unidade energizada, sem operar em regime |
| `referencia` | ruído de fundo, unidade desligada |

Apenas `normal` e `anomalia` compõem a coorte binária da Camada 3. Os demais
são preservados no conjunto: `standby` constitui regime transitório e a
`referencia` é, por definição, aquilo que se quer remover do sinal.

## Rotulagem

**A rotulagem de anomalia depende de evidência externa** — ordem de serviço,
laudo de manutenção ou observação registrada pela equipe — e nunca do próprio
áudio. Derivar o rótulo do sinal que se pretende classificar tornaria a
avaliação circular.

A evidência de cada rotulagem é preservada no repositório de dados restrito.

## Execução

```bash
# transferência do dispositivo e registro dos metadados
python -m noisedc.acquisition.transferir \
    --equipamento AC11 \
    --estado normal \
    --referencia 2026-03-12_1430_referencia.wav \
    --observacoes "coleta de rotina, corredor sem intervencao"
```

## Estrutura resultante

```
data/raw/AC11/
├── 2026-03-12_1430_normal.wav
├── 2026-03-12_1430_referencia.wav
├── 2026-03-12_1600_anomalia.wav
└── metadados.csv
```
