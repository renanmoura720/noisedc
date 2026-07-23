#!/usr/bin/env bash
# =============================================================================
# NoiseDC — execução do pipeline completo
#
#   bash scripts/run_pipeline.sh              # dados reais em data/raw
#   bash scripts/run_pipeline.sh --exemplo    # gera dados sintéticos antes
# =============================================================================
set -euo pipefail

cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH:-}:src"

if [[ ! -f configs/config.yaml ]]; then
  echo "configs/config.yaml ausente; criando a partir do modelo."
  cp configs/config.example.yaml configs/config.yaml
fi

if [[ "${1:-}" == "--exemplo" ]]; then
  echo "==> Gerando conjunto sintético de demonstração"
  python scripts/gerar_dados_exemplo.py
fi

echo "==> Camada 2: pré-processamento e extração de características"
python -m noisedc.preprocessing.run --config configs/config.yaml

echo "==> Camada 3: treinamento dos modelos"
python -m noisedc.models.train --config configs/config.yaml

echo "==> Camada 3: avaliação sob os dois protocolos"
python -m noisedc.evaluation.run --config configs/config.yaml --protocol todos

echo "==> Figuras"
python -m noisedc.viz.build_figures

echo
echo "Concluído. Resultados em results/"
echo "  métricas: results/metrics/comparativo_metodos.csv"
echo "  figuras:  results/figures/"
