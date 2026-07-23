"""Camada 3 — protocolos de particionamento.

Dois protocolos complementares, que respondem a perguntas diferentes:

``leave-one-recording-out`` (LORO)
    Reserva uma gravação inteira por vez. Mede **separabilidade
    intra-distribuição**: o modelo consegue distinguir normal de anômalo dentro
    do mesmo equipamento e das mesmas condições de coleta?

``leave-one-unit-out`` (LOUO)
    Reserva uma evaporadora inteira por vez. Mede **generalização entre
    equipamentos**: o que foi aprendido em algumas unidades vale para uma
    unidade nunca vista?

O segundo é sempre mais difícil, e a diferença entre os dois é o resultado
interessante. Particionar por segmento produziria números altos e sem
significado: segmentos vizinhos compartilham metade do sinal por causa da
sobreposição de 50%, de modo que treino e teste conteriam o mesmo áudio.
"""

from __future__ import annotations

from collections.abc import Iterator

import numpy as np
from sklearn.model_selection import LeaveOneGroupOut

PROTOCOLOS = ("leave-one-unit-out", "leave-one-recording-out")


def particoes(
    protocolo: str,
    y: np.ndarray,
    grupos: np.ndarray,
    gravacoes: np.ndarray,
    *,
    exigir_ambas_as_classes_no_teste: bool = False,
) -> Iterator[tuple[str, np.ndarray, np.ndarray]]:
    """Gera as partições de treino e teste do protocolo escolhido.

    Yields
    ------
    (nome_da_particao, indices_de_treino, indices_de_teste)

    Dobras cujo teste contém uma única classe **não** são descartadas: sob
    ``leave-one-recording-out``, toda gravação é inteiramente normal ou
    inteiramente anômala, de modo que descartá-las eliminaria o protocolo por
    inteiro. Métricas indefinidas nessas dobras (AUC, por exemplo) são
    reportadas como ``NaN`` e a avaliação consolida as predições de todas as
    dobras para calcular o resultado agregado, que é o número comparável entre
    protocolos.
    """
    if protocolo not in PROTOCOLOS:
        raise ValueError(f"Protocolo desconhecido: '{protocolo}'. Use um de {PROTOCOLOS}.")

    chaves = grupos if protocolo == "leave-one-unit-out" else gravacoes
    divisor = LeaveOneGroupOut()

    for treino, teste in divisor.split(np.zeros(len(y)), y, groups=chaves):
        nome = str(np.unique(chaves[teste])[0])

        if exigir_ambas_as_classes_no_teste and len(np.unique(y[teste])) < 2:
            continue

        yield nome, treino, teste


def contar_particoes(protocolo: str, y, grupos, gravacoes, **kwargs) -> int:
    return sum(1 for _ in particoes(protocolo, y, grupos, gravacoes, **kwargs))


def descrever_particao(y: np.ndarray, treino: np.ndarray, teste: np.ndarray) -> dict:
    """Composição de uma partição, para registro junto às métricas."""
    return {
        "n_treino": int(len(treino)),
        "n_teste": int(len(teste)),
        "treino_normais": int((y[treino] == 0).sum()),
        "treino_anomalos": int((y[treino] == 1).sum()),
        "teste_normais": int((y[teste] == 0).sum()),
        "teste_anomalos": int((y[teste] == 1).sum()),
    }
