"""Testes do módulo de configuração."""

from __future__ import annotations

import pytest

from noisedc.config import Config, ErroDeConfiguracao, variavel_de_ambiente


def test_carrega_configuracao_de_exemplo():
    from noisedc.config import RAIZ_PROJETO
    config = Config.carregar(RAIZ_PROJETO / "configs" / "config.example.yaml")
    assert config.obter("caracteristicas.n_mfcc") == 20


def test_acesso_por_caminho_pontilhado():
    config = Config(dados={"a": {"b": {"c": 42}}})
    assert config.obter("a.b.c") == 42
    assert config.obter("a.b.x", "padrao") == "padrao"


def test_exigir_levanta_erro_quando_ausente():
    config = Config(dados={})
    with pytest.raises(ErroDeConfiguracao, match="obrigatório"):
        config.exigir("inexistente")


def test_arquivo_inexistente_da_mensagem_util(tmp_path):
    with pytest.raises(ErroDeConfiguracao, match="não encontrado"):
        Config.carregar(tmp_path / "nao-existe.yaml")


def test_variavel_de_ambiente_com_padrao(monkeypatch):
    monkeypatch.delenv("NOISEDC_TESTE_VAR", raising=False)
    assert variavel_de_ambiente("NOISEDC_TESTE_VAR", "padrao") == "padrao"


def test_variavel_de_ambiente_obrigatoria_ausente(monkeypatch):
    monkeypatch.delenv("NOISEDC_TESTE_VAR", raising=False)
    with pytest.raises(ErroDeConfiguracao, match="não definida"):
        variavel_de_ambiente("NOISEDC_TESTE_VAR", obrigatoria=True)
