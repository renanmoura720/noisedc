#!/usr/bin/env bash
# =============================================================================
# NoiseDC — obtenção do conjunto de dados
#
# O áudio bruto não é distribuído pelo repositório Git: são 96 gravações, e o
# controle de versão não é o lugar para dados binários grandes. O conjunto fica
# no repositório de dados indicado em data/README.md.
# =============================================================================
set -euo pipefail

cd "$(dirname "$0")/.."

URL_DADOS="${NOISEDC_URL_DADOS:-}"   # defina no .env ou no ambiente

cat <<'TEXTO'
Conjunto de dados NoiseDC
=========================

1. Acesse o repositório de dados indicado em data/README.md
2. Baixe as pastas 01_DADOS_BRUTOS/ e 02_DADOS_PROCESSADOS/
3. Extraia em data/raw/ e data/processed/, respectivamente
4. Verifique a integridade:

     sha256sum -c data/CHECKSUMS.sha256

Estrutura esperada após a extração:

     data/raw/AC09/2026-03-12_1430_normal.wav
     data/raw/AC09/2026-03-12_1430_referencia.wav
     data/raw/AC09/metadados.csv
     ...

Para experimentar o pipeline sem os dados reais:

     python scripts/gerar_dados_exemplo.py

TEXTO

if [[ -n "$URL_DADOS" ]] && command -v curl >/dev/null; then
  echo "Baixando de \$NOISEDC_URL_DADOS..."
  mkdir -p data/raw
  curl -L "$URL_DADOS" -o data/dados.zip
  unzip -q data/dados.zip -d data/ && rm -f data/dados.zip
  echo "Concluído."
fi
