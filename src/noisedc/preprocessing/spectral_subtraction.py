"""Camada 2 — subtração espectral (Algoritmo 1 da dissertação).

O corredor de um data center é um ambiente de ruído somado: várias unidades em
operação, além do ruído de fundo da sala. A subtração espectral usa a gravação
de referência — feita com a unidade-alvo desligada ou em silêncio — para
estimar o espectro do que *não* pertence ao equipamento monitorado, e o remove
do sinal.

O piso espectral (``piso``) evita o artefato conhecido como *musical noise*:
sem ele, componentes cuja magnitude fica negativa após a subtração são zeradas
de forma abrupta, criando tons intermitentes que não existem no sinal original
e que um classificador aprenderia como padrão.
"""

from __future__ import annotations

import numpy as np


def estimar_perfil_ruido(
    referencia: np.ndarray,
    *,
    n_fft: int = 2048,
    hop_length: int = 512,
) -> np.ndarray:
    """Estima o espectro médio de magnitude da gravação de referência.

    Retorna um vetor de ``1 + n_fft // 2`` posições.
    """
    import librosa

    espectro = np.abs(librosa.stft(referencia, n_fft=n_fft, hop_length=hop_length))
    return espectro.mean(axis=1)


def subtracao_espectral(
    sinal: np.ndarray,
    perfil_ruido: np.ndarray,
    *,
    n_fft: int = 2048,
    hop_length: int = 512,
    fator: float = 1.0,
    piso: float = 0.02,
) -> np.ndarray:
    """Aplica subtração espectral e reconstrói o sinal no domínio do tempo.

    Parameters
    ----------
    fator
        Fator de super-subtração. Valores acima de 1,0 removem mais ruído ao
        custo de distorção; 1,0 corresponde à subtração clássica.
    piso
        Fração da magnitude original preservada onde a subtração resultaria em
        valor negativo.
    """
    import librosa

    espectro = librosa.stft(sinal, n_fft=n_fft, hop_length=hop_length)
    magnitude = np.abs(espectro)
    fase = np.angle(espectro)

    perfil = np.asarray(perfil_ruido, dtype=np.float64).reshape(-1, 1)
    if perfil.shape[0] != magnitude.shape[0]:
        raise ValueError(
            "Perfil de ruído incompatível com o espectro: "
            f"{perfil.shape[0]} vs {magnitude.shape[0]} bandas. "
            "Verifique se n_fft é o mesmo usado na estimativa do perfil."
        )

    limpo = magnitude - fator * perfil
    limpo = np.maximum(limpo, piso * magnitude)

    reconstruido = librosa.istft(
        limpo * np.exp(1j * fase), hop_length=hop_length, length=len(sinal)
    )
    return reconstruido.astype(np.float32)


def aplicar_com_referencia(
    sinal: np.ndarray,
    referencia: np.ndarray | None,
    *,
    n_fft: int = 2048,
    hop_length: int = 512,
    fator: float = 1.0,
    piso: float = 0.02,
) -> np.ndarray:
    """Conveniência: estima o perfil e aplica a subtração em um passo.

    Quando não há gravação de referência disponível, devolve o sinal
    inalterado. A ausência de referência é registrada nos metadados de
    proveniência para que o efeito sobre o resultado permaneça rastreável.
    """
    if referencia is None or len(referencia) == 0:
        return sinal.astype(np.float32)

    perfil = estimar_perfil_ruido(referencia, n_fft=n_fft, hop_length=hop_length)
    return subtracao_espectral(
        sinal, perfil, n_fft=n_fft, hop_length=hop_length, fator=fator, piso=piso
    )
