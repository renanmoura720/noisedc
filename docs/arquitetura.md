# Arquitetura

Quatro camadas funcionais, cada uma com um contrato de interface explícito. O
ponto da modularidade é operacional, não estético: trocar o classificador da
Camada 3 não deve exigir alteração na Camada 4, e mudar o dispositivo de coleta
não deve exigir alteração no pipeline de características.

```
   ambiente
      |
      v
+-------------------+  .wav padronizados, gravação de referência, metadados.csv
|  1. AQUISIÇÃO     | -----------------------------------------------------+
|  Arduino Yún      |                                                      |
|  + KY-037         |                                                      v
+-------------------+                                        +-------------------------+
                                                             |  2. PRÉ-PROCESSAMENTO   |
                                                             |  padronização, RMS,     |
                                                             |  subtração espectral,   |
                                                             |  segmentação, STFT,     |
                                                             |  Mel, MFCC + deltas     |
                                                             +-------------------------+
                                                                          |
                                     descritor de 60 dimensões por segmento|
                                                                          v
+-------------------------+   estado + confiança    +---------------------------------+
|  4. INTEGRAÇÃO          | <---------------------- |  3. APRENDIZADO DE MÁQUINA      |
|  Zabbix (trapper),      |                         |  baseline, SVM, Floresta        |
|  gatilhos, severidade,  |                         |  Aleatória, One-Class SVM       |
|  Grafana, SNMP          |                         +---------------------------------+
+-------------------------+
```

## Contratos entre camadas

| Fronteira | O que atravessa | Por que importa |
|---|---|---|
| 1 → 2 | arquivos `.wav` padronizados, gravação de referência, `metadados.csv` | a referência é o que viabiliza a subtração espectral; sem ela, o ruído somado do corredor domina o sinal |
| 2 → 3 | vetor de 60 dimensões por segmento, com proveniência | dimensão fixa, independente do número de quadros |
| 3 → 4 | estado (0/1) e grau de confiança | a Camada 4 depende do **formato** do registro, não do método que o produziu |

## Camada 1 — Aquisição

Protótipo IoT não intrusivo de baixo custo (aproximadamente US$ 46,10),
montado com componentes comerciais de ampla disponibilidade. A escolha por
hardware acessível é um requisito de replicabilidade, não uma limitação
orçamentária: instrumentação especializada tornaria a solução intransferível
para outros cenários de infraestrutura crítica.

Detalhes em [`hardware.md`](hardware.md) e [`protocolo-coleta.md`](protocolo-coleta.md).

## Camada 2 — Pré-processamento

Sequência aplicada a cada gravação:

1. padronização para 22.050 Hz, mono, 16 bits;
2. normalização de amplitude por RMS (alvo 0,1);
3. subtração espectral com base na gravação de referência;
4. nova normalização RMS;
5. segmentação em janelas de 2 s com 50% de sobreposição;
6. extração de STFT, Mel (128 bandas) e MFCC (20 coeficientes) + deltas.

Os arquivos brutos e as referências são preservados, de modo que o pipeline
possa ser reexecutado com parâmetros distintos sobre o mesmo material, sem nova
coleta. Essa propriedade é o que sustenta a reprodutibilidade da camada.

## Camada 3 — Aprendizado de máquina

Quatro métodos que cobrem pressupostos crescentes sobre os dados. O contraste
entre o paradigma supervisionado e o de detecção de novidade integra o próprio
objeto de análise: permite verificar qual deles se sustenta quando se exige
generalização para equipamentos não vistos.

| Método | Pressuposto | Papel |
|---|---|---|
| Baseline de limiar | nenhum modelo treinado | patamar mínimo a superar |
| SVM (RBF) | exemplos rotulados das duas classes | bom desempenho em conjuntos pequenos e de alta dimensão |
| Floresta Aleatória | idem | robustez e importância de atributos |
| One-Class SVM | apenas exemplos normais | aderente ao cenário real de escassez de falhas |

Validação por [`leave-one-unit-out` e `leave-one-recording-out`](reprodutibilidade.md).

## Camada 4 — Integração e alertas

Converte o resultado da análise em evento operacional rastreável, classificado
por severidade e comunicado à equipe. Cada evento reúne o mínimo necessário
para identificar sua origem, interpretar seu significado e rastrear o dado que
o originou: equipamento, dispositivo, momento, condição, confiança, severidade
e identificação do arquivo de áudio.

Detalhes em [`zabbix-grafana.md`](zabbix-grafana.md).
