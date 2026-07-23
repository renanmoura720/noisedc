"""Testes da Camada 2 — representações e descritores."""

from __future__ import annotations

import numpy as np
import pytest

from noisedc.features.descriptors import descritor_60d, nomes_das_dimensoes
from noisedc.features.extract import (
    ParametrosExtracao,
    energia_espectral_banda,
    espectrograma_mel_db,
    mfcc_com_deltas,
)

P = ParametrosExtracao()


def test_mfcc_produz_quarenta_linhas(sinal_normal):
    matriz = mfcc_com_deltas(sinal_normal[: 2 * P.taxa], P)
    assert matriz.shape[0] == 2 * P.n_mfcc


def test_espectrograma_mel_tem_o_numero_de_bandas(sinal_normal):
    mel = espectrograma_mel_db(sinal_normal[: 2 * P.taxa], P)
    assert mel.shape[0] == P.n_mels


def test_descritor_tem_sessenta_dimensoes(sinal_normal):
    matriz = mfcc_com_deltas(sinal_normal[: 2 * P.taxa], P)
    vetor = descritor_60d(matriz)
    assert vetor.shape == (60,)
    assert np.isfinite(vetor).all()


def test_descritor_rejeita_matriz_sem_deltas():
    with pytest.raises(ValueError, match="incluir_deltas"):
        descritor_60d(np.zeros((20, 50)))


def test_nomes_acompanham_as_dimensoes():
    assert len(nomes_das_dimensoes()) == 60


def test_energia_de_banda_detecta_componente_inserida(sinal_normal, sinal_anomalo):
    """A componente de 3 kHz do sinal anômalo deve elevar a energia na banda."""
    banda = (2500.0, 3500.0)
    trecho = slice(0, 2 * P.taxa)
    assert (
        energia_espectral_banda(sinal_anomalo[trecho], P, banda_hz=banda)
        > energia_espectral_banda(sinal_normal[trecho], P, banda_hz=banda)
    )


def test_banda_invalida_e_rejeitada(sinal_normal):
    with pytest.raises(ValueError):
        energia_espectral_banda(sinal_normal[: 2 * P.taxa], P, banda_hz=(5000.0, 1000.0))
