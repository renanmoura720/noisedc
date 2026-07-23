#!/usr/bin/env bash
# =============================================================
# NoiseDC — cria a estrutura de diretórios do repositório
# Uso: bash scripts/criar_estrutura.sh [diretorio-destino]
# =============================================================
set -euo pipefail

DESTINO="${1:-.}"
cd "$DESTINO"

DIRETORIOS=(
  ".github/workflows"
  "configs"
  "data/raw" "data/interim" "data/processed/amostras" "data/external"
  "deploy/zabbix" "deploy/grafana"
  "docs/figuras" "docs/mapeamento-sistematico" "docs/hardware"
  "notebooks"
  "results/metrics" "results/tables" "results/figures" "results/models"
  "scripts"
  "src/noisedc/acquisition"
  "src/noisedc/preprocessing"
  "src/noisedc/features"
  "src/noisedc/models"
  "src/noisedc/evaluation"
  "src/noisedc/integration"
  "src/noisedc/viz"
  "tests/fixtures"
)

for dir in "${DIRETORIOS[@]}"; do
  mkdir -p "$dir"
  # .gitkeep apenas onde o diretório pode ficar vazio no Git
  case "$dir" in
    data/*|results/models|tests/fixtures|notebooks|docs/figuras)
      touch "$dir/.gitkeep" ;;
  esac
done

# __init__.py nos pacotes Python
find src/noisedc -type d -exec touch {}/__init__.py \;

echo "Estrutura criada em: $(pwd)"
find . -type d -not -path './.git/*' | sort
