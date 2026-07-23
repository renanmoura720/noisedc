"""Fixtures compartilhadas.

Os testes usam áudio **sintético**, gerado em tempo de execução, e não amostras
do conjunto real. Duas razões: o repositório não precisa carregar arquivos de
áudio para ser testável, e o comportamento esperado fica explícito — sabemos
exatamente qual componente espectral foi inserida em cada sinal, então uma
falha aponta para o código, não para uma peculiaridade do dado.
"""

from __future__ import annotations

import numpy as np
import pytest

TAXA = 22_050
SEED = 42


def _tom(frequencia: float, duracao: float, taxa: int = TAXA, amplitude: float = 0.3) -> np.ndarray:
    t = np.linspace(0, duracao, int(taxa * duracao), endpoint=False)
    return (amplitude * np.sin(2 * np.pi * frequencia * t)).astype(np.float32)


def _ruido(duracao: float, taxa: int = TAXA, amplitude: float = 0.05, seed: int = SEED) -> np.ndarray:
    gerador = np.random.default_rng(seed)
    return (amplitude * gerador.standard_normal(int(taxa * duracao))).astype(np.float32)


@pytest.fixture
def taxa() -> int:
    return TAXA


@pytest.fixture
def sinal_normal() -> np.ndarray:
    """Ventilador em regime: fundamental em 120 Hz e harmônicos suaves."""
    return _tom(120, 6.0) + 0.4 * _tom(240, 6.0) + _ruido(6.0)


@pytest.fixture
def sinal_anomalo() -> np.ndarray:
    """Regime anômalo: componente adicional em 3 kHz, típica de rolamento."""
    return _tom(120, 6.0) + 0.4 * _tom(240, 6.0) + 0.5 * _tom(3000, 6.0) + _ruido(6.0, seed=7)


@pytest.fixture
def sinal_referencia() -> np.ndarray:
    """Ruído de fundo da sala, sem a unidade monitorada."""
    return _ruido(6.0, amplitude=0.08, seed=99)


@pytest.fixture
def conjunto_sintetico(tmp_path):
    """Cria em disco um conjunto no formato esperado pela Camada 2.

    Quatro unidades, das quais duas apresentam anomalia — proporção próxima à
    do conjunto real, em que a anomalia foi observada em poucas unidades.
    """
    import soundfile as sf

    raiz = tmp_path / "raw"
    unidades = {
        "EV09": ["normal", "normal"],
        "EV10": ["normal", "normal"],
        "EV11": ["normal", "anomalia"],
        "EV12": ["normal", "anomalia"],
    }

    for unidade, estados in unidades.items():
        pasta = raiz / unidade
        pasta.mkdir(parents=True, exist_ok=True)

        sf.write(pasta / "2026-03-12_1400_referencia.wav", _ruido(6.0, amplitude=0.08), TAXA)

        for i, estado in enumerate(estados):
            if estado == "anomalia":
                sinal = (
                    _tom(120, 6.0) + 0.4 * _tom(240, 6.0)
                    + 0.6 * _tom(3000, 6.0) + _ruido(6.0, seed=i + 11)
                )
            else:
                sinal = _tom(120, 6.0) + 0.4 * _tom(240, 6.0) + _ruido(6.0, seed=i + 3)
            sf.write(pasta / f"2026-03-12_14{i:02d}_{estado}.wav", sinal, TAXA)

    return raiz
