"""Camada 2 — segmentação temporal.

Janelas de 2 s com 50% de sobreposição, conforme a dissertação. A sobreposição
funciona como aumento de dados em nível de quadro, mas produz segmentos que
**não são observações independentes**: vizinhos compartilham metade do sinal.

Duas consequências práticas, ambas tratadas no restante do pipeline:

1. a partição de validação precisa reter unidades ou gravações inteiras, nunca
   segmentos isolados, sob pena de vazamento entre treino e teste;
2. a decisão operacional deve ser reportada também em nível de gravação, regime
   no qual a sobreposição é irrelevante.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Segmento:
    """Um trecho do sinal, com sua posição de origem preservada."""

    indice: int
    inicio_amostra: int
    sinal: np.ndarray

    @property
    def n_amostras(self) -> int:
        return len(self.sinal)

    def inicio_segundos(self, taxa: int) -> float:
        return self.inicio_amostra / float(taxa)


def segmentar(
    sinal: np.ndarray,
    taxa: int,
    *,
    janela_s: float = 2.0,
    sobreposicao: float = 0.5,
    descartar_parcial: bool = True,
) -> list[Segmento]:
    """Divide o sinal em janelas de duração fixa.

    Parameters
    ----------
    sobreposicao
        Fração de sobreposição entre janelas consecutivas, em [0, 1).
    descartar_parcial
        Descarta o último trecho quando ele é mais curto que a janela. Manter
        segmentos de duração diferente distorceria os descritores agregados.
    """
    if not 0.0 <= sobreposicao < 1.0:
        raise ValueError("sobreposicao deve estar no intervalo [0, 1)")

    n_janela = int(round(janela_s * taxa))
    if n_janela <= 0:
        raise ValueError("janela_s deve ser positiva")

    passo = max(1, int(round(n_janela * (1.0 - sobreposicao))))

    segmentos: list[Segmento] = []
    indice = 0
    for inicio in range(0, max(1, len(sinal)), passo):
        trecho = sinal[inicio : inicio + n_janela]
        if len(trecho) < n_janela:
            if descartar_parcial:
                break
            trecho = np.pad(trecho, (0, n_janela - len(trecho)))
        segmentos.append(Segmento(indice=indice, inicio_amostra=inicio, sinal=trecho))
        indice += 1  # noqa: SIM113 — indice conta segmentos válidos, não iterações do range

    return segmentos


def contar_segmentos(duracao_s: float, *, janela_s: float = 2.0, sobreposicao: float = 0.5) -> int:
    """Número de segmentos que uma gravação de dada duração produz."""
    if duracao_s < janela_s:
        return 0
    passo_s = janela_s * (1.0 - sobreposicao)
    return int((duracao_s - janela_s) // passo_s) + 1
