# Amostras de exemplo

Dois ou três segmentos por classe (`normal`, `anomalia`), incluídos para que o
repositório contenha um exemplo tangível do dado processado sem exigir o
download do conjunto completo.

Gerados por:

```bash
python scripts/gerar_dados_exemplo.py --destino /tmp/demo
python -m noisedc.preprocessing.run --entrada /tmp/demo --saida /tmp/demo_proc
cp /tmp/demo_proc/AC12/*/mfcc/seg0000.npy data/processed/amostras/
```

O conjunto completo está no repositório de dados — ver
[`../README.md`](../README.md).
