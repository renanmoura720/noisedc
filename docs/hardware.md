# Hardware do protótipo de aquisição

## Lista de materiais

| Componente | Especificação | Papel | Custo aprox. (US$) |
|---|---|---|---|
| Arduino Yún | ATmega32U4 + AR9331 com Linux embarcado (OpenWrt/Linino), Wi-Fi 802.11b/g/n, alimentação USB 5 V | controle da coleta, armazenamento temporário e transmissão | 38,00 |
| Sensor KY-037 | microfone de eletreto + comparador LM393, saídas analógica e digital | captura do sinal acústico | 2,50 |
| Cartão microSD | 8 GB ou mais | armazenamento local das gravações | 4,00 |
| Cabos e suporte | jumpers, fixação | montagem | 1,60 |
| **Total** | | | **≈ 46,10** |

## Especificações de aquisição

| Parâmetro | Valor | Observação |
|---|---|---|
| Conversor | ADC de 10 bits do ATmega32U4 | faixa de 0 a 5 V, resolução ≈ 4,9 mV |
| Taxa de amostragem | 22.050 Hz | cobertura espectral até ≈ 11 kHz |
| Formato | `.wav` mono, 16 bits | a profundidade refere-se ao contêiner |
| Saída utilizada | analógica (AO) | a digital (DO) apenas comuta em um limiar |

**Sobre a resolução efetiva.** A profundidade de 16 bits corresponde ao formato
de armazenamento; a resolução real permanece limitada pelo ADC de 10 bits do
microcontrolador. Por essa razão, o protótipo é instrumento de **análise
relativa** de padrões acústicos, e não de medição absoluta de nível sonoro.
Comparações entre sessões só são válidas após a normalização RMS aplicada na
Camada 2.

**Sobre a saída do sensor.** A saída digital do KY-037 comuta quando a
amplitude ultrapassa um limiar ajustável por potenciômetro. Ela é inadequada
para este trabalho: descarta a forma de onda, e é justamente a estrutura
espectral do sinal que carrega a informação diagnóstica.

## Montagem

```
   KY-037                     Arduino Yún
   ------                     -----------
   VCC  ------------------->  5V
   GND  ------------------->  GND
   AO   ------------------->  A0
   DO      (não utilizado)
```

Alimentação por USB 5 V. A conectividade Wi-Fi nativa viabiliza o envio dos
dados sem cabeamento adicional, o que é relevante em corredores de data center,
onde o espaço e o acesso físico são restritos.

## Firmware

O sketch está em
[`src/noisedc/acquisition/arduino_yun/coleta_acustica.ino`](../src/noisedc/acquisition/arduino_yun/coleta_acustica.ino).

As credenciais de rede aparecem como marcadores `<PREENCHER_...>` e devem ser
completadas apenas na cópia local. Antes de qualquer commit:

```bash
grep -n "PREENCHER" src/noisedc/acquisition/arduino_yun/coleta_acustica.ino
```

Credencial de Wi-Fi embutida em firmware é a via mais comum de vazamento de
acesso à rede em projetos acadêmicos de IoT — e sobrevive a qualquer limpeza
posterior do repositório, porque fica registrada no histórico.
