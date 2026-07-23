"""Camada 2 — extração de representações (Algoritmo 2 da dissertação).

Três representações complementares do mesmo segmento, e não três resultados
independentes:

* **STFT** — resolução espectral linear; preserva harmônicos e transitórios;
* **Mel (128 bandas)** — redistribui a resolução para as faixas de maior
  relevância diagnóstica, abaixo de 5 kHz no caso das evaporadoras;
* **MFCC (20) + deltas** — envelope espectral compacto e decorrelacionado,
  adequado a modelos que operam sobre vetores de características.

Os classificadores da Camada 3 usam apenas a terceira; as duas primeiras
servem à inspeção visual e a eventuais abordagens por rede convolucional.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class ParametrosExtracao:
    """Parâmetros de análise espectral, agrupados para viajar juntos."""

    taxa: int = 22_050
    n_fft: int = 2048
    hop_length: int = 512
    janela: str = "hann"
    n_mels: int = 128
    n_mfcc: int = 20
    incluir_deltas: bool = True

    @classmethod
    def da_config(cls, config) -> ParametrosExtracao:
        return cls(
            taxa=int(config.obter("aquisicao.taxa_amostragem_hz", 22_050)),
            n_fft=int(config.obter("caracteristicas.n_fft", 2048)),
            hop_length=int(config.obter("caracteristicas.hop_length", 512)),
            janela=str(config.obter("caracteristicas.janela", "hann")),
            n_mels=int(config.obter("caracteristicas.n_mels", 128)),
            n_mfcc=int(config.obter("caracteristicas.n_mfcc", 20)),
            incluir_deltas=bool(config.obter("caracteristicas.incluir_deltas", True)),
        )


def espectrograma_stft_db(sinal: np.ndarray, p: ParametrosExtracao) -> np.ndarray:
    """Espectrograma STFT em dB, normalizado pelo máximo do próprio segmento."""
    import librosa

    espectro = np.abs(
        librosa.stft(sinal, n_fft=p.n_fft, hop_length=p.hop_length, window=p.janela)
    )
    return librosa.amplitude_to_db(espectro, ref=np.max)


def espectrograma_mel_db(sinal: np.ndarray, p: ParametrosExtracao) -> np.ndarray:
    """Espectrograma Mel em dB, com ``n_mels`` bandas perceptuais."""
    import librosa

    mel = librosa.feature.melspectrogram(
        y=sinal,
        sr=p.taxa,
        n_fft=p.n_fft,
        hop_length=p.hop_length,
        window=p.janela,
        n_mels=p.n_mels,
    )
    return librosa.power_to_db(mel, ref=np.max)


def mfcc_com_deltas(sinal: np.ndarray, p: ParametrosExtracao) -> np.ndarray:
    """MFCC e suas derivadas temporais.

    Retorna matriz ``(2 * n_mfcc, n_quadros)`` quando ``incluir_deltas`` é
    verdadeiro — 40 valores por quadro na configuração da dissertação — e
    ``(n_mfcc, n_quadros)`` caso contrário.
    """
    import librosa

    coeficientes = librosa.feature.mfcc(
        y=sinal,
        sr=p.taxa,
        n_mfcc=p.n_mfcc,
        n_fft=p.n_fft,
        hop_length=p.hop_length,
        n_mels=p.n_mels,
    )
    if not p.incluir_deltas:
        return coeficientes.astype(np.float32)

    # width=3 mantém o cálculo válido para segmentos curtos; o padrão (9)
    # falha quando o número de quadros é pequeno.
    largura = min(9, _maior_impar(coeficientes.shape[1]))
    deltas = librosa.feature.delta(coeficientes, width=max(3, largura))
    return np.vstack([coeficientes, deltas]).astype(np.float32)


def _maior_impar(n: int) -> int:
    return n if n % 2 == 1 else n - 1


def energia_espectral_banda(
    sinal: np.ndarray,
    p: ParametrosExtracao,
    *,
    banda_hz: tuple[float, float],
) -> float:
    """Energia espectral média em uma faixa de frequência.

    É a característica usada pelo baseline interpretável da Camada 3. Custo
    computacional baixo e leitura direta: se a energia média na banda
    diagnóstica ultrapassa um limiar, o segmento é sinalizado.
    """
    import librosa

    f_min, f_max = banda_hz
    if f_min >= f_max:
        raise ValueError("banda_hz deve ser (minimo, maximo) com minimo < maximo")

    espectro = np.abs(
        librosa.stft(sinal, n_fft=p.n_fft, hop_length=p.hop_length, window=p.janela)
    )
    frequencias = librosa.fft_frequencies(sr=p.taxa, n_fft=p.n_fft)
    faixa = (frequencias >= f_min) & (frequencias <= f_max)
    if not faixa.any():
        raise ValueError(f"Nenhuma banda de frequência em {banda_hz} Hz para n_fft={p.n_fft}")

    return float(np.mean(np.square(espectro[faixa, :])))


def salvar_espectrograma(matriz: np.ndarray, caminho: str | Path, *, p: ParametrosExtracao,
                         eixo_mel: bool = False) -> Path:
    """Persiste um espectrograma como PNG, sem eixos nem margens.

    A imagem serve tanto à inspeção visual quanto a eventual uso como entrada
    de rede convolucional, caso em que bordas e rótulos seriam ruído.
    """
    import matplotlib

    matplotlib.use("Agg")
    import librosa.display
    import matplotlib.pyplot as plt

    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    figura, eixo = plt.subplots(figsize=(4, 3), dpi=100)
    librosa.display.specshow(
        matriz,
        sr=p.taxa,
        hop_length=p.hop_length,
        x_axis=None,
        y_axis="mel" if eixo_mel else None,
        ax=eixo,
    )
    eixo.set_axis_off()
    figura.subplots_adjust(left=0, right=1, top=1, bottom=0)
    figura.savefig(caminho, bbox_inches="tight", pad_inches=0)
    plt.close(figura)
    return caminho
