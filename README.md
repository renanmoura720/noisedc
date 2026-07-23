# NoiseDC — Arquitetura para Monitoramento e Detecção de Anomalias Acústicas em Data Centers

[![License: MIT](https://img.shields.io/badge/Código-MIT-blue.svg)](LICENSE)
[![Data: CC BY 4.0](https://img.shields.io/badge/Dados-CC%20BY%204.0-lightgrey.svg)](LICENSE-DATA)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)

Código, documentação e resultados da dissertação de mestrado **"Arquitetura para monitoramento e detecção de Anomalias Acústicas em Data Centers"**, desenvolvida no Programa de Pós-Graduação em Tecnologia da Informação (PPgTI) do Instituto Metrópole Digital — Universidade Federal do Rio Grande do Norte (IMD/UFRN).

O trabalho investiga o uso do sinal acústico emitido por evaporadoras de climatização como indicador **complementar, não intrusivo e de baixo custo** de condições anômalas, e propõe uma arquitetura modular de quatro camadas avaliada em ambiente real de produção.

---

## Sumário

- [Visão geral da arquitetura](#visão-geral-da-arquitetura)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Dados](#dados)
- [Instalação](#instalação)
- [Reprodução dos experimentos](#reprodução-dos-experimentos)
- [Resultados](#resultados)
- [Integração com Zabbix e Grafana](#integração-com-zabbix-e-grafana)
- [Limitações](#limitações)
- [Licenças](#licenças)
- [Como citar](#como-citar)
- [Contato](#contato)

---

## Visão geral da arquitetura

| Camada | Função | Entrada → Saída | Código |
|---|---|---|---|
| **1. Aquisição** | Captura não intrusiva do sinal acústico por dispositivo IoT de baixo custo (~US$ 46,10) | Sinal do ambiente → `.wav` padronizados + gravação de referência + `metadados.csv` | [`src/noisedc/acquisition/`](src/noisedc/acquisition) |
| **2. Pré-processamento** | Padronização, normalização RMS, subtração espectral, segmentação e extração de representações | `.wav` → STFT, Mel (128 bandas), MFCC (20 + deltas) | [`src/noisedc/preprocessing/`](src/noisedc/preprocessing), [`src/noisedc/features/`](src/noisedc/features) |
| **3. Aprendizado de máquina** | Classificação do estado operacional | Vetores MFCC → rótulo + grau de confiança | [`src/noisedc/models/`](src/noisedc/models), [`src/noisedc/evaluation/`](src/noisedc/evaluation) |
| **4. Integração e alertas** | Ingestão, gatilhos, severidade, notificação e correlação com métricas SNMP | Estado + confiança → eventos, alertas e histórico | [`src/noisedc/integration/`](src/noisedc/integration), [`deploy/`](deploy) |

**Ambiente experimental:** seis evaporadoras APC InRow RD (EV09–EV14), Corredor C do Data Center do IMD/UFRN.

**Parâmetros do pipeline:** áudio mono, 22.050 Hz, 16 bits; janelas de 2 s com 50% de sobreposição; `NFFT = 2048`; `hop = 512`; janela de Hann; 128 filtros Mel; 20 MFCC + 20 deltas (40 valores por quadro).

**Métodos comparados:** baseline de limiar único (energia espectral na banda diagnóstica), SVM (RBF, `C = 1,0`, `class_weight = balanced`), Floresta Aleatória (100 árvores) e One-Class SVM (RBF, `ν = 0,5`, treinado apenas com segmentos normais).

**Validação:** `leave-one-recording-out` (separabilidade intra-distribuição) e `leave-one-unit-out` (generalização para unidades não vistas), com métricas reportadas em nível de segmento e de gravação.

---

## Estrutura do repositório

```text
noisedc/
├── configs/           # parâmetros do pipeline (versionados) e config.example.yaml
├── data/              # apenas metadados e amostras leves; áudio no Google Drive
├── deploy/            # template Zabbix e dashboards Grafana (sanitizados)
├── docs/              # arquitetura, hardware, protocolo de coleta, dicionário de dados
├── notebooks/         # análises exploratórias
├── results/           # métricas, tabelas, figuras e modelos treinados
├── scripts/           # execução do pipeline e verificação de dados sensíveis
├── src/noisedc/       # código-fonte por camada da arquitetura
└── tests/             # testes automatizados
```

---

## Dados

Os dados seguem o princípio **"código no GitHub, dados no Drive"**. O repositório contém apenas metadados, amostras leves e artefatos derivados pequenos; áudio bruto, espectrogramas e vetores completos ficam no repositório de dados.

| Artefato | Volume | Local | Acesso |
|---|---|---|---|
| Áudio bruto (`.wav`) + gravações de referência | 96 gravações | Google Drive | Público mediante solicitação |
| Espectrogramas STFT e Mel (`.png`) | 2.818 segmentos | Google Drive | Público |
| Vetores MFCC (`.npy`) | 2.818 segmentos | Google Drive | Público |
| `metadados_processados.csv` | 2.818 linhas | Este repositório (`data/processed/`) | Público |
| Evidências de rotulagem das anomalias | — | Google Drive | Restrito |

**Repositório de dados:** <!-- INSERIR LINK DO GOOGLE DRIVE -->
**DOI do conjunto de dados:** <!-- INSERIR DOI DO ZENODO -->

O dicionário de dados e o mapeamento completo entre repositório e Drive estão em [`data/README.md`](data/README.md) e [`docs/dicionario-de-dados.md`](docs/dicionario-de-dados.md).

---

## Instalação

Requisitos: Python 3.10 ou superior.

```bash
git clone https://github.com/<usuario>/noisedc.git
cd noisedc
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # preencha com seus próprios endereços e credenciais
cp configs/config.example.yaml configs/config.yaml
```

Nenhum endereço de servidor, credencial ou token institucional é distribuído neste repositório. A Camada 4 só é executável após o preenchimento local do `.env`.

---

## Reprodução dos experimentos

```bash
# 1. Baixar os dados do repositório de dados para data/raw/
bash scripts/baixar_dados.sh

# 2. Camada 2 — pré-processamento e extração de características
python -m noisedc.preprocessing.run --config configs/config.yaml

# 3. Camada 3 — treinamento e avaliação dos quatro métodos
python -m noisedc.models.train --config configs/config.yaml
python -m noisedc.evaluation.run --protocol leave-one-unit-out
python -m noisedc.evaluation.run --protocol leave-one-recording-out

# 4. Figuras e tabelas da dissertação
python -m noisedc.viz.build_figures

# Alternativa: pipeline completo
make all
```

A semente aleatória é fixada em `configs/config.yaml` (`seed: 42`). Padronização por *z-score* e ajuste de limiar são estimados **exclusivamente na partição de treino** de cada dobra, para evitar vazamento.

---

## Resultados

As métricas (acurácia, precisão, recall, F1, AUC e taxa de falsos positivos), as matrizes de confusão e as figuras utilizadas na dissertação são geradas em `results/`:

```text
results/
├── metrics/   # *.csv e *.json por método e protocolo de validação
├── tables/    # tabelas em formato LaTeX correspondentes à dissertação
├── figures/   # espectrogramas, matrizes de confusão, curvas ROC, desempenho por unidade
└── models/    # modelos serializados (.joblib) e scalers
```

Cada arquivo de métrica registra o método, o protocolo de validação, o nível de agregação (segmento ou gravação) e a dobra correspondente, permitindo rastrear qualquer número reportado no texto até o script que o produziu.

---

## Integração com Zabbix e Grafana

A Camada 4 publica, para cada equipamento (host), dois itens do tipo *trapper*:

| Item | Tipo | Descrição |
|---|---|---|
| `acustico.estado` | inteiro | `0` = normal, `1` = anômalo |
| `acustico.confianca` | ponto flutuante | grau de confiança da classificação |

O envio é feito com `zabbix_sender` sobre o protocolo nativo da plataforma. O template `snitch-InRow` encapsula itens, gatilhos e severidades e é vinculado a cada host, de modo que incorporar um novo ativo se resume a registrar o host e vincular o template. Métricas convencionais (temperatura, carga e parâmetros elétricos) são coletadas por SNMP em template próprio, no mesmo host, permitindo correlacionar o indício acústico com o contexto operacional.

Os artefatos em [`deploy/`](deploy) são **exportações sanitizadas**: endereços, comunidades SNMP, usuários, chaves e nomes internos foram substituídos por marcadores no formato `<PREENCHER>`. Consulte [`docs/zabbix-grafana.md`](docs/zabbix-grafana.md) para importação e configuração.

---

## Limitações

Os resultados devem ser lidos considerando que o estudo se apoia em um único modelo de equipamento e em um único ambiente; que anomalias foram observadas em apenas duas unidades, o que limita a estimativa de generalização entre equipamentos; que os segmentos com 50% de sobreposição não são observações estatisticamente independentes, razão pela qual a decisão operacional também é reportada em nível de gravação; e que o protótipo, por usar sensoriamento de baixo custo com ADC de 10 bits, é instrumento de **análise relativa** de padrões acústicos, não de medição absoluta de nível sonoro.

---

## Licenças

| Conteúdo | Licença |
|---|---|
| Código-fonte (`src/`, `scripts/`, `notebooks/`) | [MIT](LICENSE) |
| Dados, figuras, documentação e resultados | [CC BY 4.0](LICENSE-DATA) |
| Texto da dissertação | Termos do Repositório Institucional da UFRN |

---

## Como citar

Se este trabalho for útil à sua pesquisa, cite a dissertação:

```bibtex
@mastersthesis{silva2026noisedc,
  author       = {Silva, Renan Moura da},
  title        = {Arquitetura para monitoramento e detec{\c{c}}{\~a}o de Anomalias
                  Ac{\'u}sticas em Data Centers},
  school       = {Universidade Federal do Rio Grande do Norte},
  address      = {Natal, RN, Brasil},
  year         = {2026},
  type         = {Disserta{\c{c}}{\~a}o de Mestrado},
  note         = {Programa de P{\'o}s-Gradua{\c{c}}{\~a}o em Tecnologia da
                  Informa{\c{c}}{\~a}o, Instituto Metr{\'o}pole Digital}
}
```

Para citar o software ou o conjunto de dados especificamente, utilize o DOI do Zenodo. O arquivo [`CITATION.cff`](CITATION.cff) permite que o GitHub gere a citação automaticamente pelo botão *Cite this repository*.

---

## Contato

**Renan Moura da Silva** — <!-- e-mail de contato --> — ORCID: <!-- INSERIR -->
**Orientador:** Prof. Dr. Roger Kreutz Immich — IMD/UFRN

Dúvidas sobre reprodução, acesso aos dados ou colaborações podem ser registradas em [Issues](../../issues).
