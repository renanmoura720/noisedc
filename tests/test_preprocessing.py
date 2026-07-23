"""Testes da Camada 2 — condicionamento do sinal."""

from __future__ import annotations

import numpy as np

from noisedc.preprocessing.audio import normalizar_rms, rms
from noisedc.preprocessing.segmentation import contar_segmentos, segmentar
from noisedc.preprocessing.spectral_subtraction import (
    aplicar_com_referencia,
    estimar_perfil_ruido,
    subtracao_espectral,
)


def test_normalizacao_rms_atinge_o_alvo(sinal_normal):
    normalizado = normalizar_rms(sinal_normal, alvo=0.1)
    assert rms(normalizado) == np.float32(np.float64(rms(normalizado)))
    assert abs(rms(normalizado) - 0.1) < 1e-4


def test_normalizacao_preserva_sinal_silencioso():
    """Um sinal nulo não deve ser amplificado até o alvo."""
    silencio = np.zeros(1000, dtype=np.float32)
    assert np.allclose(normalizar_rms(silencio), silencio)


def test_segmentacao_com_sobreposicao(sinal_normal, taxa):
    segmentos = segmentar(sinal_normal, taxa, janela_s=2.0, sobreposicao=0.5)
    assert len(segmentos) == contar_segmentos(6.0, janela_s=2.0, sobreposicao=0.5)
    assert all(s.n_amostras == 2 * taxa for s in segmentos)
    # 50% de sobreposição: o segundo segmento começa na metade do primeiro
    assert segmentos[1].inicio_amostra == taxa


def test_segmentacao_descarta_trecho_parcial(taxa):
    sinal = np.zeros(int(2.5 * taxa), dtype=np.float32)
    segmentos = segmentar(sinal, taxa, janela_s=2.0, sobreposicao=0.5)
    assert all(s.n_amostras == 2 * taxa for s in segmentos)


def test_subtracao_espectral_reduz_a_componente_do_ruido(sinal_normal, sinal_referencia):
    perfil = estimar_perfil_ruido(sinal_referencia)
    limpo = subtracao_espectral(sinal_normal + sinal_referencia, perfil)
    assert len(limpo) == len(sinal_normal)
    # a energia total deve cair após remover a contribuição do ruído
    assert rms(limpo) < rms(sinal_normal + sinal_referencia)


def test_sem_referencia_o_sinal_passa_intacto(sinal_normal):
    assert np.allclose(aplicar_com_referencia(sinal_normal, None), sinal_normal)
