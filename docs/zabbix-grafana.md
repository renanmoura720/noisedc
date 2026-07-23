# Integração com Zabbix e Grafana

## Modelo de dados

Cada evaporadora é um host. Sob ele, dois itens do tipo *trapper* recebem os
valores enviados pelo pipeline:

| Item | Tipo | Conteúdo |
|---|---|---|
| `acustico.estado` | inteiro | 0 = normal, 1 = anômalo |
| `acustico.confianca` | ponto flutuante | grau de confiança da classificação, em [0, 1] |

Itens *trapper* recebem valores enviados ativamente por agentes externos, sem
polling. A escolha decorre da natureza do processamento: a classificação
acontece em lote, ao final de cada conjunto de gravações, e não em resposta a
uma consulta do servidor.

## Por que o contrato é estreito

A Camada 4 depende apenas do **formato do registro recebido**, não do método
que o produziu. Trocar o classificador da Camada 3 — ou substituí-lo por uma
rede convolucional sobre espectrogramas — não exige alteração alguma na
integração. Essa separação é o que permite evoluir o modelo sem renegociar a
configuração de monitoramento com a equipe de infraestrutura.

## Severidades

| Nível | Condição | Ação recomendada |
|---|---|---|
| Aviso | anomalia com confiança abaixo do patamar mínimo | variação acústica leve; registrar para histórico |
| Médio | anomalia com confiança entre o patamar e 0,95 | alteração perceptível; acompanhar e correlacionar com temperatura e carga |
| Alto | anomalia com confiança igual ou superior a 0,95 | padrão incompatível com a operação normal; inspeção presencial |

O disparo é condicionado a um patamar mínimo de confiança (`{$ACUSTICO.CONFIANCA.MIN}`,
padrão 0,80) para reduzir alarmes espúrios provocados por eventos sonoros
transitórios — uma porta que bate, uma conversa próxima ao sensor.

Há ainda um gatilho de **ausência de dados**: um coletor que parou de enviar é
indistinguível de um equipamento sem anomalia, e essa ambiguidade precisa gerar
alerta próprio.

## Publicação de um resultado

```bash
# simulação: mostra o que seria enviado, sem enviar
python -m noisedc.integration.run \
    --audio data/raw/AC11/2026-03-12_1430_normal.wav \
    --referencia data/raw/AC11/2026-03-12_1430_referencia.wav \
    --modelo results/models/floresta_aleatoria.joblib \
    --equipamento AC11

# envio efetivo, com .env preenchido
python -m noisedc.integration.run --audio ... --enviar
```

O modo de simulação é o padrão deliberadamente: ninguém deve disparar alertas
em produção apenas por seguir o README.

## Correlação com métricas SNMP

As métricas convencionais das unidades — temperatura, carga e parâmetros
elétricos — são expostas pelas placas de gerência e coletadas por SNMP em
template próprio, operando de forma desacoplada **no mesmo host**.

Reunir as duas naturezas de informação sob o mesmo host é o que permite avaliar
um indício acústico à luz do contexto operacional: verificar se uma anomalia
sonora é acompanhada de variação simultânea de temperatura ou de carga reduz
substancialmente a ambiguidade das detecções.

## Escalabilidade

O template `snitch-InRow` encapsula itens, gatilhos, severidades e ações.
Vinculado ao host de cada evaporadora, o conjunto inteiro é herdado sem
reconfiguração individual: **incorporar um novo ativo reduz-se a registrar um
host e vincular o template existente**.

## Importação

Instruções em [`../deploy/README.md`](../deploy/README.md). Os artefatos em
`deploy/` são exportações sanitizadas: endereços, comunidades SNMP, usuários e
nomes internos foram substituídos por marcadores `<PREENCHER>`.
