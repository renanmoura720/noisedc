"""Testes da Camada 3 — protocolos e métricas."""

from __future__ import annotations

import numpy as np

from noisedc.evaluation.metrics import (
    agregar_por_gravacao,
    calcular_metricas,
    matriz_de_confusao,
)
from noisedc.evaluation.protocols import particoes


def test_metricas_perfeitas():
    y = np.array([0, 0, 1, 1])
    m = calcular_metricas(y, y, escores=np.array([0.0, 0.1, 0.9, 1.0]))
    assert m["acuracia"] == 1.0
    assert m["recall"] == 1.0
    assert m["taxa_falsos_positivos"] == 0.0
    assert m["auc"] == 1.0


def test_taxa_de_falsos_positivos():
    y = np.array([0, 0, 0, 0])
    predito = np.array([0, 1, 0, 1])
    assert calcular_metricas(y, predito)["taxa_falsos_positivos"] == 0.5


def test_matriz_de_confusao_tem_rotulos():
    matriz = matriz_de_confusao(np.array([0, 1]), np.array([0, 1]))
    assert matriz.shape == (2, 2)
    assert "predito: anomalia" in matriz.columns


def test_leave_one_unit_out_isola_a_unidade():
    y = np.array([0, 1, 0, 1, 0, 1])
    grupos = np.array(["AC09", "AC09", "AC10", "AC10", "AC11", "AC11"])
    gravacoes = np.array(["g1", "g1", "g2", "g2", "g3", "g3"])

    for nome, treino, teste in particoes("leave-one-unit-out", y, grupos, gravacoes):
        # nenhuma amostra da unidade de teste pode aparecer no treino
        assert nome not in set(grupos[treino])
        assert set(grupos[teste]) == {nome}


def test_agregacao_por_gravacao_consolida_segmentos():
    gravacoes = np.array(["g1", "g1", "g1", "g2", "g2"])
    y = np.array([1, 1, 1, 0, 0])
    escores = np.array([0.9, 0.8, 0.7, 0.1, 0.2])

    rotulos, agregados, _predicoes, ids = agregar_por_gravacao(gravacoes, y, escores)
    assert list(ids) == ["g1", "g2"]
    assert list(rotulos) == [1, 0]
    assert agregados[0] > agregados[1]
