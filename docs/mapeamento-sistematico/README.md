# Mapeamento sistemático da literatura

Protocolo, execução e resultados da revisão de literatura da dissertação
(Capítulo 2), publicada como artigo completo no **XVIII Simpósio Brasileiro
de Computação Ubíqua e Pervasiva (SBCUP 2026)**. Este mapeamento identificou
as lacunas de padronização metodológica e de integração que orientaram o
projeto da arquitetura NoiseDC — é referenciado no Capítulo 6 da dissertação
como uma das contribuições principais do trabalho.

## Publicação

> MOURA, R.; DALMAZO, B. L.; RIKER, A.; FONTES, R.; FILHO, I. M. B.; IMMICH, R.
> **Detecção e Monitoramento de Anomalias em Data Centers Através de Análise
> Acústica: Abordagens e Direções Futuras**. In: *Anais do XVIII Simpósio
> Brasileiro de Computação Ubíqua e Pervasiva (SBCUP 2026)*. Porto Alegre,
> RS: SBC, 2026. p. <!-- PREENCHER -->. DOI: <!-- PREENCHER, se houver -->.

**Autoria e afiliações:**

| Autor | Instituição | E-mail |
|---|---|---|
| Renan Moura | UFRN | renan.moura@imd.ufrn.br |
| Bruno L. Dalmazo | FURG | dalmazo@furg.br |
| André Riker | UFPA | ariker@ufpa.br |
| Ramon Fontes | UFRN | ramon.fontes@imd.ufrn.br |
| Itamir M. B. Filho | UFRN | itamir.filho@imd.ufrn.br |
| Roger Immich | UFRN | roger@imd.ufrn.br |

```bibtex
@inproceedings{moura2026sbcup,
  author    = {Moura, Renan and Dalmazo, Bruno L. and Riker, André and
               Fontes, Ramon and Filho, Itamir M. B. and Immich, Roger},
  title     = {Detecção e Monitoramento de Anomalias em Data Centers Através
               de Análise Acústica: Abordagens e Direções Futuras},
  booktitle = {Anais do XVIII Simpósio Brasileiro de Computação Ubíqua e
               Pervasiva (SBCUP 2026)},
  year      = {2026},
  publisher = {SBC},
  address   = {Porto Alegre, RS},
  pages     = {} % PREENCHER
}
```

> ⚠️ **Nota de manutenção.** O artigo publicado aponta, em nota de rodapé,
> para o repositório institucional
> `https://projetosdti.imd.ufrn.br/msl-noisedc` como local dos artefatos
> abertos. Esse endereço é um projeto GitLab que exige autenticação
> institucional — não está de fato aberto ao público, ainda que o texto do
> artigo declare "repositório público no GitHub". Isso é uma pendência
> conhecida: idealmente, o README daquele projeto deveria ser atualizado
> para redirecionar a quem chega pelo artigo até
> [`github.com/renan-ppgti/noisedc`](https://github.com/renan-ppgti/noisedc),
> que é o repositório efetivamente público.

## Objetivo e questões de pesquisa

O mapeamento identifica, organiza e analisa estudos sobre o uso de sinais
acústicos em ambientes de data center, com foco em monitoramento e detecção
de anomalias, orientado por quatro questões de pesquisa:

- **RQ1.** Como evoluiu a produção científica sobre análise de ruído em data
  centers ao longo do tempo, e quais são as abordagens mais utilizadas?
- **RQ2.** Quais ativos de data centers são mais investigados quanto a seus
  padrões sonoros e potenciais anomalias acústicas?
- **RQ3.** Quais combinações entre fontes de sinal, técnicas de análise e
  objetivos de monitoramento foram identificadas para detecção de falhas e
  manutenção preditiva?
- **RQ4.** Quais são as principais lacunas identificadas nos estudos sobre
  monitoramento do ruído em infraestruturas de data centers?

## Metodologia

Seguiu-se a metodologia de Petersen et al. (2008), em quatro fases: questões
de pesquisa, condução da busca, seleção de trabalhos e extração/mapeamento
dos dados. A busca foi conduzida em quatro mecanismos de busca acadêmica —
**ACM Digital Library, IEEE Xplore, ScienceDirect e Scopus** — por título,
resumo e palavras-chave.

**String de busca (adaptada por base):**
`("datacenter" OR "data center" OR "data processing center" OR "DCIM")
AND ("noise" OR "sound" [OR "audio"])`

**Critérios de inclusão:** estudos que abordam análise de ruído/som em data
centers; estudos que detectam falhas baseadas em ruído/som em data centers.

**Critérios de exclusão:** artigo duplicado; *short paper* (≤3 páginas);
literatura cinza; publicado antes de 2015; indisponível; estudo secundário
(revisão/mapeamento); fora de escopo; trabalho em andamento; idioma diferente
de inglês/português.

**Funil de seleção:**

| Etapa | Quantidade |
|---|---|
| Resultados da busca | 3.576 |
| Após remoção de duplicados | 2.710 |
| Potencialmente relevantes (após CI/CE) | 37 |
| Selecionados (após leitura completa) | **29** |

## Taxonomia proposta

O mapeamento propõe uma taxonomia em cinco dimensões articuladas, que
organiza o domínio e evidencia combinações pouco exploradas entre elas:

| Dimensão | Categorias |
|---|---|
| **Fontes do sinal** | sistemas de resfriamento, equipamentos computacionais, infraestrutura física, eventos operacionais, ambiente acústico global |
| **Arquitetura de sensoriamento** | sensores pontuais, distribuídos, integrados, ambientais |
| **Técnicas de análise** | processamento de sinais, análise estatística, aprendizado de máquina, aprendizado profundo, simulação física |
| **Objetivos do monitoramento** | detecção de falhas, manutenção preventiva, monitoramento ambiental, segurança e canais laterais, otimização operacional |
| **Escala de monitoramento** | componente, equipamento, sistema, infraestrutura |

Achado central da taxonomia: **sensores acústicos dedicados são raros** na
literatura revisada (representatividade baixa frente a sensores integrados,
pontuais, distribuídos e ambientais) — é exatamente a lacuna que a
arquitetura NoiseDC deste repositório propõe endereçar.

## Principais achados por questão de pesquisa

- **RQ1** — crescimento recente e concentrado: caracterização determinística
  do ruído entre 2015–2017; diversificação (falhas, segurança) entre
  2018–2021; consolidação com IA/aprendizado profundo a partir de 2022–2025.
- **RQ2** — sistemas de resfriamento e ventilação (ventiladores, HVAC) são os
  ativos mais investigados; servidores/racks como fontes acústicas integradas;
  HDDs quanto à sensibilidade a ruído intenso.
- **RQ3** — equipamentos computacionais e eventos operacionais convergem
  majoritariamente para sensores integrados, alimentando processamento de
  sinais, *deep learning* e análise de vibração voltados à detecção de
  falhas e manutenção preditiva.
- **RQ4** — quatro lacunas estruturais: (1) ausência de estudos
  longitudinais sobre efeitos cumulativos da exposição acústica; (2) falta de
  padronização metodológica (métricas, faixas espectrais, limiares,
  protocolos de validação); (3) integração ainda incipiente com outras
  fontes de telemetria; (4) escassez de validação em ambientes operacionais
  reais — esta última é precisamente a lacuna que a validação em produção
  desta dissertação (Capítulo 5) preenche.

## Materiais de apoio

| Arquivo | Conteúdo |
|---|---|
| `protocolo.md` | questões de pesquisa, critérios de inclusão/exclusão, bases consultadas *(a incluir)* |
| `strings-de-busca.md` | strings completas por base *(a incluir)* |
| `planilha-triagem.csv` | os 29 estudos selecionados, com decisão e justificativa *(a incluir)* |
| `diagrama-selecao.png` | fluxo de seleção (Figura 1 do artigo) *(a incluir)* |

O artigo publicado também disponibiliza visualizações complementares —
gráficos analíticos e um diagrama de Sankey interativo (Figura 8) explorando
as relações entre fonte, sensoriamento, técnica e objetivo.
