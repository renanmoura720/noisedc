"""Camada 2 — extração de representações e descritores."""

from noisedc.features.descriptors import descritor_60d, nomes_das_dimensoes
from noisedc.features.extract import (
    ParametrosExtracao,
    energia_espectral_banda,
    espectrograma_mel_db,
    espectrograma_stft_db,
    mfcc_com_deltas,
)

__all__ = [
    "descritor_60d", "nomes_das_dimensoes", "ParametrosExtracao",
    "energia_espectral_banda", "espectrograma_mel_db", "espectrograma_stft_db",
    "mfcc_com_deltas",
]
