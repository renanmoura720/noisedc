"""Camada 3 — métricas de avaliação.

Além das métricas usuais, reporta-se explicitamente a **taxa de falsos
positivos**: em ambiente operacional, o volume de alarmes espúrios determina se
a equipe passa a confiar ou a ignorar o sistema, e uma acurácia agregada alta
pode conviver com uma taxa de falsos positivos inaceitável quando as classes
são desbalanceadas.

Pela mesma razão, a acurácia agregada é reportada mas não é o critério de
comparação: com 1.749 segmentos normais para 290 anômalos, um classificador que
sempre responde "normal" atinge 86% de acurácia sem detectar uma única falha.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

NORMAL = 0
ANOMALIA = 1


def calcular_metricas(
    y_verdadeiro: np.ndarray,
    y_predito: np.ndarray,
    escores: np.ndarray | None = None,
) -> dict[str, float]:
    """Conjunto completo de métricas para uma partição."""
    y_verdadeiro = np.asarray(y_verdadeiro, dtype=int)
    y_predito = np.asarray(y_predito, dtype=int)

    matriz = confusion_matrix(y_verdadeiro, y_predito, labels=[NORMAL, ANOMALIA])
    vn, fp, fn, vp = matriz.ravel()

    resultado = {
        "acuracia": float(accuracy_score(y_verdadeiro, y_predito)),
        "precisao": float(precision_score(y_verdadeiro, y_predito, pos_label=ANOMALIA, zero_division=0)),
        "recall": float(recall_score(y_verdadeiro, y_predito, pos_label=ANOMALIA, zero_division=0)),
        "f1": float(f1_score(y_verdadeiro, y_predito, pos_label=ANOMALIA, zero_division=0)),
        "taxa_falsos_positivos": float(fp / (fp + vn)) if (fp + vn) > 0 else float("nan"),
        "verdadeiros_negativos": int(vn),
        "falsos_positivos": int(fp),
        "falsos_negativos": int(fn),
        "verdadeiros_positivos": int(vp),
    }

    if escores is not None and len(np.unique(y_verdadeiro)) == 2:
        resultado["auc"] = float(roc_auc_score(y_verdadeiro, np.asarray(escores, dtype=float)))
    else:
        resultado["auc"] = float("nan")

    return resultado


def matriz_de_confusao(y_verdadeiro: np.ndarray, y_predito: np.ndarray) -> pd.DataFrame:
    """Matriz de confusão rotulada, pronta para exportação."""
    matriz = confusion_matrix(y_verdadeiro, y_predito, labels=[NORMAL, ANOMALIA])
    return pd.DataFrame(
        matriz,
        index=pd.Index(["real: normal", "real: anomalia"], name=""),
        columns=pd.Index(["predito: normal", "predito: anomalia"], name=""),
    )


def agregar_por_gravacao(
    gravacoes: np.ndarray,
    y_verdadeiro: np.ndarray,
    escores: np.ndarray,
    predicoes: np.ndarray | None = None,
    *,
    fracao_minima: float = 0.5,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Consolida a decisão por segmento em decisão por gravação.

    A agregação existe porque segmentos com 50% de sobreposição não são
    observações independentes. Em nível de gravação a sobreposição é
    irrelevante, e o número resultante corresponde à decisão operacional que a
    Camada 4 efetivamente toma.

    A regra é a mesma usada em operação: a gravação é sinalizada quando a
    fração de segmentos positivos supera ``fracao_minima``. O escore agregado
    é a média dos escores dos segmentos, usada para calcular a AUC.

    Returns
    -------
    (rotulos_verdadeiros, escores_agregados, predicoes_agregadas, identificadores)
    """
    gravacoes = np.asarray(gravacoes)
    y_verdadeiro = np.asarray(y_verdadeiro, dtype=int)
    escores = np.asarray(escores, dtype=float)
    if predicoes is None:
        predicoes = (escores > 0).astype(int)
    predicoes = np.asarray(predicoes, dtype=int)

    identificadores = np.unique(gravacoes)
    rotulos = np.zeros(len(identificadores), dtype=int)
    escores_agregados = np.zeros(len(identificadores), dtype=float)
    predicoes_agregadas = np.zeros(len(identificadores), dtype=int)

    for i, identificador in enumerate(identificadores):
        seletor = gravacoes == identificador
        # A rotulagem de origem é por gravação: se qualquer segmento é anômalo,
        # a gravação inteira o é.
        rotulos[i] = int(y_verdadeiro[seletor].max())
        escores_agregados[i] = float(escores[seletor].mean())
        predicoes_agregadas[i] = int(float(predicoes[seletor].mean()) > fracao_minima)

    return rotulos, escores_agregados, predicoes_agregadas, identificadores


def consolidar(resultados: list[dict]) -> pd.DataFrame:
    """Consolida as métricas de várias partições em uma tabela com médias.

    A média entre partições é reportada com o desvio-padrão porque, sob
    ``leave-one-unit-out`` com poucas unidades anômalas, a variância entre
    dobras costuma ser maior que a diferença entre métodos — e omitir esse
    dado faria uma diferença de ruído parecer um resultado.
    """
    if not resultados:
        return pd.DataFrame()

    tabela = pd.DataFrame(resultados)
    numericas = tabela.select_dtypes(include="number").columns

    resumo = tabela[numericas].agg(["mean", "std"]).T
    resumo.columns = ["media", "desvio_padrao"]
    return resumo.reset_index().rename(columns={"index": "metrica"})
