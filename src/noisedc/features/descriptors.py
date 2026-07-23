"""Camada 2 — descritor de dimensão fixa por segmento.

A matriz MFCC tem forma ``40 x n_quadros``, e o número de quadros varia com a
duração efetiva do segmento. Os classificadores da Camada 3 precisam de um
vetor de tamanho constante, obtido por agregação temporal:

* média e desvio-padrão de cada um dos 20 coeficientes cepstrais → 40 valores;
* média de cada um dos 20 deltas → 20 valores.

Total: **60 dimensões**, exatamente como reportado na dissertação. O descritor
sintetiza nível e variabilidade espectral do trecho sem expor os modelos à
dimensionalidade das matrizes completas.

O desvio-padrão dos deltas é deliberadamente omitido: ele mede a variação da
variação, é dominado por ruído em janelas de 2 s e, em conjuntos pequenos,
acrescenta dimensões sem acrescentar informação.
"""

from __future__ import annotations

import numpy as np

N_MFCC_PADRAO = 20


def descritor_60d(mfcc_com_deltas: np.ndarray, n_mfcc: int = N_MFCC_PADRAO) -> np.ndarray:
    """Agrega a matriz MFCC+deltas em um vetor de 60 dimensões.

    Parameters
    ----------
    mfcc_com_deltas
        Matriz ``(2 * n_mfcc, n_quadros)`` produzida por
        :func:`noisedc.features.extract.mfcc_com_deltas`.
    """
    matriz = np.asarray(mfcc_com_deltas, dtype=np.float64)
    if matriz.ndim != 2:
        raise ValueError(f"Esperada matriz 2D, recebida forma {matriz.shape}")

    esperado = 2 * n_mfcc
    if matriz.shape[0] != esperado:
        raise ValueError(
            f"Esperadas {esperado} linhas (MFCC + deltas), recebidas {matriz.shape[0]}. "
            "Confirme se 'incluir_deltas' está habilitado na configuração."
        )

    coeficientes = matriz[:n_mfcc, :]
    deltas = matriz[n_mfcc:, :]

    return np.concatenate(
        [
            coeficientes.mean(axis=1),   # 20
            coeficientes.std(axis=1),    # 20
            deltas.mean(axis=1),         # 20
        ]
    ).astype(np.float32)


def nomes_das_dimensoes(n_mfcc: int = N_MFCC_PADRAO) -> list[str]:
    """Rótulos das 60 dimensões, úteis em gráficos de importância de atributos."""
    return (
        [f"mfcc{i + 1}_media" for i in range(n_mfcc)]
        + [f"mfcc{i + 1}_desvio" for i in range(n_mfcc)]
        + [f"delta{i + 1}_media" for i in range(n_mfcc)]
    )


def matriz_de_descritores(lista_mfcc: list[np.ndarray], n_mfcc: int = N_MFCC_PADRAO) -> np.ndarray:
    """Empilha descritores de vários segmentos em uma matriz ``(n_segmentos, 60)``."""
    if not lista_mfcc:
        return np.empty((0, 3 * n_mfcc), dtype=np.float32)
    return np.vstack([descritor_60d(m, n_mfcc=n_mfcc) for m in lista_mfcc])
