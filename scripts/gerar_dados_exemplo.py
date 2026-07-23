#!/usr/bin/env python3
"""Gera um conjunto acústico sintético para experimentar o pipeline.

Serve a quem clona o repositório e quer executar a cadeia completa antes de
solicitar acesso ao conjunto real: o áudio é gerado localmente, o formato é
idêntico ao esperado pela Camada 2 e nenhuma transferência é necessária.

O sinal "normal" simula um ventilador em regime — fundamental grave e alguns
harmônicos — e o "anômalo" acrescenta uma componente em torno de 3 kHz, na
faixa em que a literatura associa alterações a desgaste de rolamentos.

**Os resultados obtidos sobre este conjunto não têm significado científico.**
Ele existe para validar a instalação e o encadeamento das camadas, não para
reproduzir os achados da dissertação.

Uso::

    python scripts/gerar_dados_exemplo.py
    python scripts/gerar_dados_exemplo.py --destino /tmp/demo --unidades 6
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

TAXA = 22_050
DURACAO_S = 10.0


def tom(frequencia: float, duracao: float, amplitude: float, taxa: int = TAXA) -> np.ndarray:
    t = np.linspace(0, duracao, int(taxa * duracao), endpoint=False)
    return amplitude * np.sin(2 * np.pi * frequencia * t)


def ruido(duracao: float, amplitude: float, gerador: np.random.Generator, taxa: int = TAXA) -> np.ndarray:
    return amplitude * gerador.standard_normal(int(taxa * duracao))


def sinal_normal(gerador: np.random.Generator) -> np.ndarray:
    """Ventilador em regime, com leve variação de rotação entre unidades."""
    fundamental = 120.0 + gerador.uniform(-4, 4)
    return (
        tom(fundamental, DURACAO_S, 0.30)
        + tom(2 * fundamental, DURACAO_S, 0.12)
        + tom(3 * fundamental, DURACAO_S, 0.05)
        + ruido(DURACAO_S, 0.04, gerador)
    )


def sinal_anomalo(gerador: np.random.Generator) -> np.ndarray:
    """Mesmo regime, com componente adicional na faixa diagnóstica."""
    return sinal_normal(gerador) + tom(3000 + gerador.uniform(-200, 200), DURACAO_S, 0.18)


def sinal_referencia(gerador: np.random.Generator) -> np.ndarray:
    """Ruído de fundo da sala, sem a unidade monitorada."""
    return ruido(DURACAO_S, 0.06, gerador) + tom(60, DURACAO_S, 0.03)


def gerar(destino: Path, n_unidades: int = 4, seed: int = 42) -> Path:
    import soundfile as sf

    gerador = np.random.default_rng(seed)
    destino.mkdir(parents=True, exist_ok=True)

    # A anomalia ocorre em poucas unidades, como no conjunto real.
    unidades_anomalas = {f"EV{9 + n_unidades - 1:02d}", f"EV{9 + n_unidades - 2:02d}"}

    for i in range(n_unidades):
        unidade = f"EV{9 + i:02d}"
        pasta = destino / unidade
        pasta.mkdir(parents=True, exist_ok=True)

        sf.write(pasta / "2026-03-12_1400_referencia.wav", sinal_referencia(gerador), TAXA)

        for sessao in range(3):
            hora = f"14{sessao * 10:02d}"
            sf.write(pasta / f"2026-03-12_{hora}_normal.wav", sinal_normal(gerador), TAXA)

        if unidade in unidades_anomalas:
            for sessao in range(2):
                hora = f"15{sessao * 10:02d}"
                sf.write(pasta / f"2026-03-12_{hora}_anomalia.wav", sinal_anomalo(gerador), TAXA)

    print(f"Conjunto sintético gerado em {destino}")
    print(f"{n_unidades} unidades, anomalia em: {', '.join(sorted(unidades_anomalas))}")
    print("\nPróximo passo:")
    print("  python -m noisedc.preprocessing.run --entrada", destino, "--sem-imagens")
    return destino


def principal(argv: list[str] | None = None) -> int:
    raiz = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Gera dados sintéticos de demonstração")
    parser.add_argument("--destino", default=str(raiz / "data" / "raw"))
    parser.add_argument("--unidades", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    gerar(Path(args.destino), n_unidades=args.unidades, seed=args.seed)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
