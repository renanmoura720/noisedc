"""Camada 2 — carregamento e condicionamento do sinal.

Implementa as duas primeiras operações do pipeline descrito na dissertação:
padronização para 22.050 Hz / mono / 16 bits e normalização de amplitude por
RMS com alvo 0,1.

A normalização por RMS é o que torna comparáveis gravações feitas em sessões
diferentes: como o protótipo usa sensoriamento de baixo custo e o nível
absoluto depende de posicionamento e ganho, o interesse está no *padrão*
espectral, não na amplitude absoluta.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

TAXA_PADRAO = 22_050
RMS_ALVO_PADRAO = 0.1


def carregar_audio(
    caminho: str | Path,
    taxa_alvo: int = TAXA_PADRAO,
    *,
    mono: bool = True,
) -> tuple[np.ndarray, int]:
    """Carrega um arquivo de áudio e o padroniza para a taxa de trabalho.

    Retorna o sinal em ``float32`` no intervalo aproximado [-1, 1] e a taxa
    efetiva de amostragem.
    """
    import librosa  # importado aqui para manter o custo fora do import do pacote

    sinal, taxa = librosa.load(str(caminho), sr=taxa_alvo, mono=mono)
    return sinal.astype(np.float32), int(taxa)


def rms(sinal: np.ndarray) -> float:
    """Valor eficaz do sinal."""
    if sinal.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(sinal, dtype=np.float64))))


def normalizar_rms(
    sinal: np.ndarray,
    alvo: float = RMS_ALVO_PADRAO,
    *,
    epsilon: float = 1e-10,
) -> np.ndarray:
    """Escala o sinal para que seu RMS seja igual a ``alvo``.

    Sinais silenciosos são devolvidos inalterados: multiplicar ruído de fundo
    por um ganho enorme para atingir o alvo introduziria artefatos que o
    classificador aprenderia como se fossem informação.
    """
    atual = rms(sinal)
    if atual < epsilon:
        return sinal.astype(np.float32)
    return (sinal * (alvo / atual)).astype(np.float32)


def limitar(sinal: np.ndarray, limite: float = 1.0) -> np.ndarray:
    """Satura o sinal, evitando estouro na escrita de arquivos de 16 bits."""
    return np.clip(sinal, -limite, limite).astype(np.float32)


def duracao_segundos(sinal: np.ndarray, taxa: int) -> float:
    return float(len(sinal)) / float(taxa)
