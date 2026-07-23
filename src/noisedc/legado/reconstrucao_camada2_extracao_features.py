#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Camada 2 — reconstrução do script de extração de características (Linha C, EV09-EV14).

⚠️  RECONSTRUÇÃO, NÃO O ORIGINAL. Diferente de
    camada3_autoritativo_linha_c.py (enviado pelo autor e preservado
    byte-a-byte), este script foi reescrito a partir do esquema observado no
    features_segmentos.csv real e da descrição do pipeline no Capítulo 4 da
    dissertação. Produz um CSV com exatamente as mesmas colunas do arquivo
    real, mas os valores não foram conferidos número a número contra nenhuma
    tabela publicada — ao contrário da Camada 3, esta camada gera dados de
    entrada, não métricas finais, então não há tabela do texto para validar
    diretamente. Trate como ponto de partida a ser substituído pelo script
    original assim que ele for localizado.

Convenção de nome de arquivo observada nos dados reais:

    LINHAC-EV{unidade:02d}-{AAAAMMDD}-{turno}-{codigo}-{sequencial:03d}.wav

  turno   ∈ {manh, tarde, noite}
  codigo  ∈ {OFF, ANOM, OK, STBY, BOOTOK, BOOTANOM}
            mapeando para condicao ∈ {DESLIGADA, ANOMALIA, OK, STANDBY,
            BOOT_OK, BOOT_ANOMALO}
  Gravações de boot têm data placeholder "00000000" nos dados reais —
  presume-se que o instante de partida não fica associado a uma sessão
  calendário específica, e este script preserva essa convenção.

Saída: features_segmentos.csv
  colunas: sample_id, evaporadora, linha, classe, condicao, seg_idx,
           mfcc{1..20}_mean, mfcc{1..20}_std, dmfcc{1..20}_mean,
           rms, zcr, centroid, rolloff

Descritor usado pela Camada 3 (60 dimensões): mfcc*_mean + mfcc*_std +
dmfcc*_mean. As colunas rms/zcr/centroid/rolloff são características
adicionais persistidas para uso exploratório, mas não entram no descritor
da Camada 3 (que filtra apenas colunas mfcc*/dmfcc*).
"""
from __future__ import annotations

import csv
import re
import warnings
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")

# --- parâmetros do pipeline (Capítulo 4) ---
TAXA_HZ = 22_050
N_FFT = 2048
HOP_LENGTH = 512
JANELA = "hann"
N_MFCC = 20
JANELA_SEGMENTO_S = 2.0
SOBREPOSICAO = 0.5
RMS_ALVO = 0.1
LINHA = "C"

# --- caminhos (ajuste conforme sua árvore) ---
ENTRADA = Path("dataset_linhaC/01_dados_brutos")
SAIDA = Path("dataset_linhaC/04_resultados/features_segmentos.csv")

CODIGO_PARA_CONDICAO = {
    "OFF": "DESLIGADA",
    "ANOM": "ANOMALIA",
    "OK": "OK",
    "STBY": "STANDBY",
    "BOOTOK": "BOOT_OK",
    "BOOTANOM": "BOOT_ANOMALO",
}
CONDICAO_PARA_CLASSE = {
    "DESLIGADA": "desligada",
    "ANOMALIA": "anomalia",
    "OK": "normal",
    "STANDBY": "standby",
    "BOOT_OK": "normal",
    "BOOT_ANOMALO": "anomalia",
}

PADRAO_NOME = re.compile(
    r"^LINHAC-EV(?P<unidade>\d{2})-(?P<data>\d{8})-(?P<turno>manh|tarde|noite)"
    r"-(?P<codigo>OFF|ANOM|OK|STBY|BOOTOK|BOOTANOM)-(?P<sequencial>\d{3})$"
)

COLUNAS = (
    ["sample_id", "evaporadora", "linha", "classe", "condicao", "seg_idx"]
    + [c for i in range(1, N_MFCC + 1) for c in (f"mfcc{i}_mean", f"mfcc{i}_std")]
    + [f"dmfcc{i}_mean" for i in range(1, N_MFCC + 1)]
    + ["rms", "zcr", "centroid", "rolloff"]
)


def interpretar_nome(caminho: Path) -> dict | None:
    """Extrai unidade, data, turno, condição e sequencial do nome do arquivo."""
    m = PADRAO_NOME.match(caminho.stem)
    if not m:
        return None
    campos = m.groupdict()
    condicao = CODIGO_PARA_CONDICAO[campos["codigo"]]
    return {
        "evaporadora": int(campos["unidade"]),
        "data": campos["data"],
        "turno": campos["turno"],
        "condicao": condicao,
        "classe": CONDICAO_PARA_CLASSE[condicao],
        "sequencial": int(campos["sequencial"]),
    }


def normalizar_rms(sinal: np.ndarray, alvo: float = RMS_ALVO) -> np.ndarray:
    atual = float(np.sqrt(np.mean(np.square(sinal, dtype=np.float64))))
    if atual < 1e-10:
        return sinal.astype(np.float32)
    return (sinal * (alvo / atual)).astype(np.float32)


def subtrair_referencia(sinal: np.ndarray, referencia: np.ndarray | None) -> np.ndarray:
    """Subtração espectral usando a gravação de referência da mesma sessão."""
    import librosa

    if referencia is None or len(referencia) == 0:
        return sinal
    perfil = np.abs(librosa.stft(referencia, n_fft=N_FFT, hop_length=HOP_LENGTH)).mean(axis=1)
    espectro = librosa.stft(sinal, n_fft=N_FFT, hop_length=HOP_LENGTH)
    magnitude, fase = np.abs(espectro), np.angle(espectro)
    limpo = np.maximum(magnitude - perfil.reshape(-1, 1), 0.02 * magnitude)
    return librosa.istft(limpo * np.exp(1j * fase), hop_length=HOP_LENGTH, length=len(sinal))


def segmentar(sinal: np.ndarray, taxa: int) -> list[np.ndarray]:
    n_janela = int(round(JANELA_SEGMENTO_S * taxa))
    passo = int(round(n_janela * (1 - SOBREPOSICAO)))
    segmentos = []
    for inicio in range(0, len(sinal) - n_janela + 1, passo):
        segmentos.append(sinal[inicio : inicio + n_janela])
    return segmentos


def extrair_caracteristicas(segmento: np.ndarray, taxa: int) -> dict:
    """MFCC + deltas (descritor da Camada 3) e características auxiliares."""
    import librosa

    mfcc = librosa.feature.mfcc(
        y=segmento, sr=taxa, n_mfcc=N_MFCC, n_fft=N_FFT, hop_length=HOP_LENGTH
    )
    deltas = librosa.feature.delta(mfcc, width=min(9, max(3, mfcc.shape[1] - (mfcc.shape[1] % 2 == 0))))

    linha = {}
    for i in range(N_MFCC):
        linha[f"mfcc{i + 1}_mean"] = float(mfcc[i].mean())
        linha[f"mfcc{i + 1}_std"] = float(mfcc[i].std())
    for i in range(N_MFCC):
        linha[f"dmfcc{i + 1}_mean"] = float(deltas[i].mean())

    linha["rms"] = float(librosa.feature.rms(y=segmento, hop_length=HOP_LENGTH).mean())
    linha["zcr"] = float(librosa.feature.zero_crossing_rate(segmento, hop_length=HOP_LENGTH).mean())
    linha["centroid"] = float(
        librosa.feature.spectral_centroid(y=segmento, sr=taxa, hop_length=HOP_LENGTH).mean()
    )
    linha["rolloff"] = float(
        librosa.feature.spectral_rolloff(y=segmento, sr=taxa, hop_length=HOP_LENGTH).mean()
    )
    return linha


def localizar_referencia(caminho: Path, metadados: dict) -> Path | None:
    """Procura a gravação DESLIGADA mais próxima da mesma unidade e sessão."""
    candidatos = sorted(caminho.parent.glob(f"LINHAC-EV{metadados['evaporadora']:02d}-*-OFF-*.wav"))
    mesma_data = [c for c in candidatos if metadados["data"] in c.stem]
    if mesma_data:
        return mesma_data[0]
    return candidatos[0] if candidatos else None


def processar_arquivo(caminho: Path) -> list[dict]:
    import librosa

    metadados = interpretar_nome(caminho)
    if metadados is None:
        print(f"  aviso: nome fora do padrão, ignorado: {caminho.name}")
        return []

    sinal, taxa = librosa.load(str(caminho), sr=TAXA_HZ, mono=True)
    sinal = normalizar_rms(sinal)

    if metadados["condicao"] != "DESLIGADA":
        referencia_path = localizar_referencia(caminho, metadados)
        referencia = None
        if referencia_path is not None:
            referencia, _ = librosa.load(str(referencia_path), sr=TAXA_HZ, mono=True)
            referencia = normalizar_rms(referencia)
        sinal = normalizar_rms(subtrair_referencia(sinal, referencia))

    linhas = []
    for seg_idx, segmento in enumerate(segmentar(sinal, taxa)):
        linha = {
            "sample_id": caminho.stem,
            "evaporadora": metadados["evaporadora"],
            "linha": LINHA,
            "classe": metadados["classe"],
            "condicao": metadados["condicao"],
            "seg_idx": seg_idx,
        }
        linha.update(extrair_caracteristicas(segmento, taxa))
        linhas.append(linha)
    return linhas


def main() -> None:
    arquivos = sorted(ENTRADA.rglob("LINHAC-*.wav"))
    if not arquivos:
        raise SystemExit(
            f"Nenhum arquivo LINHAC-*.wav encontrado em {ENTRADA}. "
            "Ajuste a constante ENTRADA no topo do script."
        )

    print(f"{len(arquivos)} arquivos encontrados em {ENTRADA}")
    SAIDA.parent.mkdir(parents=True, exist_ok=True)

    todas_as_linhas: list[dict] = []
    for i, caminho in enumerate(arquivos, start=1):
        print(f"[{i}/{len(arquivos)}] {caminho.name}")
        todas_as_linhas.extend(processar_arquivo(caminho))

    with SAIDA.open("w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUNAS)
        escritor.writeheader()
        escritor.writerows(todas_as_linhas)

    print(f"\n{len(todas_as_linhas)} segmentos gravados em {SAIDA}")


if __name__ == "__main__":
    main()
