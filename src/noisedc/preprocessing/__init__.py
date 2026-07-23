"""Camada 2 — condicionamento do sinal acústico."""

from noisedc.preprocessing.audio import carregar_audio, normalizar_rms, rms
from noisedc.preprocessing.segmentation import Segmento, segmentar
from noisedc.preprocessing.spectral_subtraction import (
    aplicar_com_referencia,
    estimar_perfil_ruido,
    subtracao_espectral,
)

__all__ = [
    "carregar_audio", "normalizar_rms", "rms",
    "Segmento", "segmentar",
    "aplicar_com_referencia", "estimar_perfil_ruido", "subtracao_espectral",
]
