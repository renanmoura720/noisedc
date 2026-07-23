"""Testes da Camada 3 — métodos de classificação."""

from __future__ import annotations

import numpy as np
import pytest

from noisedc.models.registry import METODOS, BaselineLimiar, DetectorNovidade, criar_modelo


@pytest.fixture
def dados_separaveis():
    gerador = np.random.default_rng(42)
    normais = gerador.normal(0.0, 1.0, size=(80, 60))
    anomalos = gerador.normal(3.0, 1.0, size=(20, 60))
    X = np.vstack([normais, anomalos])
    y = np.concatenate([np.zeros(80, dtype=int), np.ones(20, dtype=int)])
    return X, y


@pytest.mark.parametrize("metodo", METODOS)
def test_todos_os_metodos_expoem_a_mesma_interface(metodo, dados_separaveis):
    X, y = dados_separaveis
    if metodo == "baseline":
        X = X[:, :1]

    modelo = criar_modelo(metodo)
    modelo.fit(X, y)

    predito = modelo.predict(X)
    escores = modelo.decision_function(X)

    assert predito.shape == (len(y),)
    assert escores.shape == (len(y),)
    assert set(np.unique(predito)) <= {0, 1}


def test_baseline_ajusta_limiar_no_treino():
    X = np.array([[1.0], [1.2], [0.9], [5.0], [5.5]])
    y = np.array([0, 0, 0, 1, 1])

    modelo = BaselineLimiar().fit(X, y)
    assert 1.2 <= modelo.limiar_ < 5.0
    assert list(modelo.predict(X)) == [0, 0, 0, 1, 1]


def test_baseline_recusa_multiplas_caracteristicas():
    with pytest.raises(ValueError, match="escalar"):
        BaselineLimiar().fit(np.zeros((10, 3)), np.zeros(10, dtype=int))


def test_detector_de_novidade_treina_apenas_com_normais(dados_separaveis):
    X, y = dados_separaveis
    modelo = DetectorNovidade(nu=0.1).fit(X, y)
    # o escalonador deve ter visto apenas os 80 exemplos normais
    assert modelo.escalador_.n_samples_seen_ == 80


def test_escore_maior_indica_anomalia(dados_separaveis):
    X, y = dados_separaveis
    modelo = criar_modelo("floresta_aleatoria").fit(X, y)
    escores = modelo.decision_function(X)
    assert escores[y == 1].mean() > escores[y == 0].mean()


def test_metodo_desconhecido_e_rejeitado():
    with pytest.raises(ValueError, match="Método desconhecido"):
        criar_modelo("rede_neural")
