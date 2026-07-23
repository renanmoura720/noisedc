# Dados

Este diretório **não contém áudio bruto**. O repositório Git guarda apenas
metadados, amostras mínimas e artefatos derivados leves; o material pesado fica
no repositório de dados no Google Drive.

## Mapa repositório ↔ Google Drive

| Caminho no repositório | Conteúdo | Origem no Drive |
|---|---|---|
| `data/raw/` | vazio (`.gitkeep`) | `01_DADOS_BRUTOS/` |
| `data/interim/` | vazio (`.gitkeep`) | gerado localmente |
| `data/processed/metadados_processados.csv` | metadados dos 2.818 segmentos | também em `02_DADOS_PROCESSADOS/` |
| `data/processed/amostras/` | 2 a 3 segmentos de exemplo por classe | `02_DADOS_PROCESSADOS/` |
| `data/external/` | vazio (`.gitkeep`) | — |

## Como obter os dados

```bash
bash scripts/baixar_dados.sh          # ou download manual pelo link do Drive
sha256sum -c data/CHECKSUMS.sha256    # verificação de integridade
```

## Estrutura esperada após o download

```text
data/raw/
├── AC09/
│   ├── 2026-03-12_1430_normal.wav
│   ├── 2026-03-12_1430_referencia.wav
│   └── metadados.csv
├── AC10/ ... AC14/
└── referencia_ruido_fundo/
```

## Dicionário de dados

`metadados_processados.csv` — uma linha por segmento:

| Campo | Tipo | Descrição |
|---|---|---|
| `arquivo_origem` | texto | caminho relativo do `.wav` que originou o segmento |
| `indice_segmento` | inteiro | posição do segmento dentro da gravação |
| `equipamento` | texto | identificador da unidade (AC09–AC14) |
| `estado` | categórico | `normal`, `anomalia`, `standby` ou `referencia` |
| `caminho_stft` | texto | espectrograma STFT (`.png`) |
| `caminho_mel` | texto | espectrograma Mel (`.png`) |
| `caminho_mfcc` | texto | vetor de características (`.npy`) |
| `sessao_coleta` | texto | identificador da sessão |
| `timestamp` | ISO 8601 | início da gravação |

Os segmentos rotulados como `standby` e `referencia` são preservados no
conjunto, mas ficam fora da coorte binária utilizada na Camada 3.

## Termos de uso

Dados sob CC BY 4.0 (ver `LICENSE-DATA`). Ao redistribuir, mantenha a
atribuição e o vínculo com a dissertação de origem.
