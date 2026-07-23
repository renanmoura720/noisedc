"""Camada 3 — os quatro métodos de classificação.

O conjunto reúne paradigmas distintos, e não variações do mesmo:

* **Baseline de limiar único** — sem treinamento de modelo, fixa o patamar
  mínimo que os métodos de aprendizado precisam superar para justificar sua
  adoção;
* **SVM** e **Floresta Aleatória** — supervisionados, aprendem a fronteira
  entre normal e anomalia a partir de exemplos rotulados das duas classes;
* **One-Class SVM** — detector de novidade, treinado apenas com o estado
  normal, o que o torna o mais aderente ao cenário real de escassez de falhas.

Todos expõem a mesma interface (``fit``, ``predict``, ``decision_function``),
com escore contínuo em que **valores maiores indicam maior evidência de
anomalia**. Essa convenção é o que permite calcular AUC e curvas ROC de forma
uniforme na Camada de avaliação.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC, OneClassSVM

NORMAL = 0
ANOMALIA = 1


class BaselineLimiar(BaseEstimator, ClassifierMixin):
    """Classificador de limiar único sobre uma característica escalar.

    O limiar é ajustado por varredura **exclusivamente sobre o conjunto de
    treino de cada partição**, maximizando a medida F1, e então aplicado ao
    conjunto de teste correspondente. Ajustá-lo sobre o teste produziria um
    baseline artificialmente forte e invalidaria a comparação.

    Espera uma matriz de uma única coluna: a energia espectral média na banda
    diagnóstica, calculada na Camada 2.
    """

    def __init__(self, n_limiares: int = 200):
        self.n_limiares = n_limiares

    def fit(self, X: np.ndarray, y: np.ndarray) -> BaselineLimiar:
        X = np.asarray(X, dtype=float).reshape(len(X), -1)
        if X.shape[1] != 1:
            raise ValueError(
                f"BaselineLimiar espera uma característica escalar, recebidas {X.shape[1]}."
            )
        valores = X[:, 0]
        y = np.asarray(y, dtype=int)

        candidatos = np.quantile(valores, np.linspace(0.0, 1.0, self.n_limiares))
        candidatos = np.unique(candidatos)

        melhor_limiar, melhor_f1 = float(np.median(valores)), -1.0
        for limiar in candidatos:
            predito = (valores > limiar).astype(int)
            escore = f1_score(y, predito, pos_label=ANOMALIA, zero_division=0)
            if escore > melhor_f1:
                melhor_limiar, melhor_f1 = float(limiar), float(escore)

        self.limiar_ = melhor_limiar
        self.f1_treino_ = melhor_f1
        self.classes_ = np.array([NORMAL, ANOMALIA])
        return self

    def decision_function(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float).reshape(len(X), -1)
        return X[:, 0] - self.limiar_

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.decision_function(X) > 0).astype(int)


class DetectorNovidade(BaseEstimator, ClassifierMixin):
    """Adaptador do One-Class SVM à interface dos demais métodos.

    Treina apenas com os segmentos do estado normal, como prescreve a
    formulação de detecção de novidade, e converte a saída ``+1/-1`` do
    scikit-learn para a convenção do projeto (``0`` normal, ``1`` anomalia).

    O valor de ``nu`` limita superiormente a fração de exemplos tratados como
    anomalia no treino. O padrão de 0,5 é conservador e contribui diretamente
    para a taxa de falsos positivos observada; sua calibração conjunta com o
    patamar de confiança da Camada 4 é ajuste operacional, não científico.
    """

    def __init__(self, kernel: str = "rbf", nu: float = 0.5, gamma: str | float = "scale"):
        self.kernel = kernel
        self.nu = nu
        self.gamma = gamma

    def fit(self, X: np.ndarray, y: np.ndarray | None = None) -> DetectorNovidade:
        X = np.asarray(X, dtype=float)
        if y is not None:
            y = np.asarray(y, dtype=int)
            X_treino = X[y == NORMAL]
            if len(X_treino) == 0:
                raise ValueError(
                    "Nenhum segmento normal na partição de treino; "
                    "o detector de novidade não pode ser ajustado."
                )
        else:
            X_treino = X

        self.escalador_ = StandardScaler().fit(X_treino)
        self.modelo_ = OneClassSVM(kernel=self.kernel, nu=self.nu, gamma=self.gamma)
        self.modelo_.fit(self.escalador_.transform(X_treino))
        self.classes_ = np.array([NORMAL, ANOMALIA])
        return self

    def decision_function(self, X: np.ndarray) -> np.ndarray:
        # O sinal é invertido: no scikit-learn, valores altos indicam
        # normalidade; aqui, valores altos indicam anomalia.
        return -self.modelo_.decision_function(self.escalador_.transform(np.asarray(X, dtype=float)))

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.decision_function(X) > 0).astype(int)


class EnvelopeSupervisionado(BaseEstimator, ClassifierMixin):
    """Envolve um classificador supervisionado padronizando o escore de saída.

    Garante que ``decision_function`` sempre devolva um escore em que valores
    maiores significam maior evidência de anomalia, independentemente de o
    modelo interno expor ``decision_function`` ou ``predict_proba``.
    """

    def __init__(self, estimador: Any):
        self.estimador = estimador

    def fit(self, X: np.ndarray, y: np.ndarray) -> EnvelopeSupervisionado:
        self.estimador_ = self.estimador.fit(X, y)
        self.classes_ = np.array([NORMAL, ANOMALIA])
        return self

    def decision_function(self, X: np.ndarray) -> np.ndarray:
        if hasattr(self.estimador_, "predict_proba"):
            probabilidades = self.estimador_.predict_proba(X)
            indice = list(self.estimador_.classes_).index(ANOMALIA)
            return probabilidades[:, indice]
        return self.estimador_.decision_function(X)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.estimador_.predict(X)


def criar_modelo(nome: str, config=None) -> BaseEstimator:
    """Instancia um dos quatro métodos, com os parâmetros da configuração.

    Os valores de referência de cada método são usados deliberadamente, sem
    otimização extensiva de hiperparâmetros: com anomalias observadas em apenas
    duas unidades, uma busca agressiva ajustaria o modelo às particularidades
    dessas ocorrências e comprometeria justamente a estimativa de generalização
    que o estudo pretende avaliar.
    """
    def cfg(chave: str, padrao):
        return padrao if config is None else config.obter(chave, padrao)

    nome = nome.lower().replace("-", "_")

    if nome == "baseline":
        return BaselineLimiar()

    if nome == "svm":
        return EnvelopeSupervisionado(
            Pipeline(
                [
                    ("escalador", StandardScaler()),
                    (
                        "svm",
                        SVC(
                            kernel=str(cfg("modelos.svm.kernel", "rbf")),
                            C=float(cfg("modelos.svm.C", 1.0)),
                            gamma=cfg("modelos.svm.gamma", "scale"),
                            class_weight=cfg("modelos.svm.class_weight", "balanced"),
                        ),
                    ),
                ]
            )
        )

    if nome in {"floresta_aleatoria", "rf", "random_forest"}:
        return EnvelopeSupervisionado(
            RandomForestClassifier(
                n_estimators=int(cfg("modelos.floresta_aleatoria.n_estimators", 100)),
                max_depth=cfg("modelos.floresta_aleatoria.max_depth", None),
                max_features=cfg("modelos.floresta_aleatoria.max_features", "sqrt"),
                random_state=int(cfg("projeto.seed", 42)),
                n_jobs=-1,
            )
        )

    if nome in {"one_class_svm", "ocsvm"}:
        return DetectorNovidade(
            kernel=str(cfg("modelos.one_class_svm.kernel", "rbf")),
            nu=float(cfg("modelos.one_class_svm.nu", 0.5)),
            gamma=cfg("modelos.one_class_svm.gamma", "scale"),
        )

    raise ValueError(
        f"Método desconhecido: '{nome}'. "
        "Disponíveis: baseline, svm, floresta_aleatoria, one_class_svm."
    )


METODOS = ("baseline", "svm", "floresta_aleatoria", "one_class_svm")

ROTULOS_LEGIVEIS = {
    "baseline": "Baseline (limiar único)",
    "svm": "SVM (RBF)",
    "floresta_aleatoria": "Floresta Aleatória",
    "one_class_svm": "One-Class SVM",
}


def usa_apenas_energia(nome: str) -> bool:
    """Indica se o método opera sobre a energia de banda em vez do descritor 60D."""
    return nome.lower() == "baseline"
