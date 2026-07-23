"""Teste de ponta a ponta: Camada 2 -> Camada 3 -> Camada 4."""

from __future__ import annotations

from pathlib import Path

import pytest

from noisedc.config import Config
from noisedc.dataset import carregar_coorte
from noisedc.evaluation.run import executar as avaliar
from noisedc.models.train import executar as treinar
from noisedc.preprocessing.run import executar as preprocessar


@pytest.fixture
def config():
    return Config.carregar(Path(__file__).resolve().parents[1] / "configs" / "config.example.yaml")


def test_pipeline_completo(conjunto_sintetico, tmp_path, config):
    processado = tmp_path / "processed"
    preprocessar(conjunto_sintetico, processado, config, salvar_imagens=False)

    metadados = processado / "metadados_processados.csv"
    assert metadados.exists()

    coorte = carregar_coorte(metadados)
    assert coorte.X.shape[1] == 60
    assert set(coorte.y) == {0, 1}
    assert len(set(coorte.grupos)) == 4

    modelos = treinar(["svm", "floresta_aleatoria"], coorte, config, tmp_path / "models")
    assert all(m.exists() for m in modelos)

    comparativo = avaliar(
        coorte, config, ["leave-one-unit-out"], ["baseline", "svm"], tmp_path / "metrics"
    )
    assert not comparativo.empty
    assert (tmp_path / "metrics" / "comparativo_metodos.csv").exists()
