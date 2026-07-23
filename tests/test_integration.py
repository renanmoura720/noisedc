"""Testes da Camada 4 — eventos e integração."""

from __future__ import annotations

from noisedc.integration.zabbix import ClienteZabbix, Evento, escrever_lote


def test_evento_normal_nao_e_anomalo():
    evento = Evento(equipamento="AC11", estado=0, confianca=0.95)
    assert not evento.anomalo
    assert evento.severidade() == "informativo"


def test_severidade_cresce_com_a_confianca():
    baixa = Evento("AC11", 1, 0.60).severidade(confianca_minima=0.80)
    media = Evento("AC11", 1, 0.85).severidade(confianca_minima=0.80)
    alta = Evento("AC11", 1, 0.99).severidade(confianca_minima=0.80)
    assert (baixa, media, alta) == ("aviso", "medio", "alto")


def test_dicionario_do_evento_tem_rastreabilidade():
    dados = Evento("AC11", 1, 0.9, arquivo_audio="a.wav", dispositivo="snitch-01").como_dicionario()
    assert dados["arquivo_audio"] == "a.wav"
    assert dados["dispositivo"] == "snitch-01"
    assert "momento" in dados


def test_modo_de_simulacao_nao_exige_servidor():
    cliente = ClienteZabbix(simular=True)
    comandos = cliente.enviar_evento(Evento("AC11", 1, 0.9))
    assert len(comandos) == 2
    assert "acustico.estado" in comandos[0]
    assert "acustico.confianca" in comandos[1]


def test_arquivo_de_lote_tem_duas_linhas_por_evento(tmp_path):
    destino = escrever_lote(
        [Evento("AC11", 1, 0.9), Evento("AC12", 0, 0.8)], tmp_path / "lote.txt"
    )
    linhas = destino.read_text(encoding="utf-8").strip().splitlines()
    assert len(linhas) == 4
    assert linhas[0].startswith("AC11 acustico.estado")
