"""Camada 3 — protocolos de validação e métricas."""

from noisedc.evaluation.metrics import (
    agregar_por_gravacao,
    calcular_metricas,
    matriz_de_confusao,
)
from noisedc.evaluation.protocols import PROTOCOLOS, particoes

__all__ = [
    "agregar_por_gravacao", "calcular_metricas", "matriz_de_confusao",
    "PROTOCOLOS", "particoes",
]
