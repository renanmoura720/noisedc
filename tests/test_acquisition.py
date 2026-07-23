"""Testes da Camada 1 — transferência e registro de metadados."""

from __future__ import annotations

from noisedc.acquisition.transferir import copiar_de_pasta, registrar_metadados


def test_copia_arquivos_wav_de_pasta_local(tmp_path):
    origem = tmp_path / "origem"
    origem.mkdir()
    (origem / "a.wav").write_bytes(b"RIFF....")
    (origem / "b.wav").write_bytes(b"RIFF....")
    (origem / "notas.txt").write_text("ignorar")

    destino = tmp_path / "destino"
    copiados = copiar_de_pasta(origem, destino)

    assert len(copiados) == 2
    assert all(c.suffix == ".wav" for c in copiados)


def test_registrar_metadados_cria_planilha_com_cabecalho(tmp_path):
    pasta = tmp_path / "AC11"
    pasta.mkdir()
    arquivos = [pasta / "g1.wav", pasta / "g2.wav"]
    for a in arquivos:
        a.touch()

    planilha = registrar_metadados(
        pasta, arquivos, equipamento="AC11", estado="normal", sessao="2026-03-12_1400"
    )

    conteudo = planilha.read_text(encoding="utf-8")
    assert "arquivo,equipamento,estado" in conteudo
    assert "g1.wav" in conteudo and "g2.wav" in conteudo


def test_registrar_metadados_nao_duplica_registros(tmp_path):
    pasta = tmp_path / "AC11"
    pasta.mkdir()
    arquivo = pasta / "g1.wav"
    arquivo.touch()

    registrar_metadados(pasta, [arquivo], equipamento="AC11", estado="normal", sessao="s1")
    planilha = registrar_metadados(pasta, [arquivo], equipamento="AC11", estado="normal", sessao="s1")

    linhas = planilha.read_text(encoding="utf-8").strip().splitlines()
    assert len(linhas) == 2  # cabeçalho + 1 registro, sem duplicar
