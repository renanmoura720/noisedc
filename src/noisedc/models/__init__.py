"""Camada 3 — métodos de classificação."""

from noisedc.models.registry import (
    METODOS,
    BaselineLimiar,
    DetectorNovidade,
    criar_modelo,
)

__all__ = ["METODOS", "BaselineLimiar", "DetectorNovidade", "criar_modelo"]
