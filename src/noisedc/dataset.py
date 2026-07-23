"""Montagem da coorte de classificação a partir dos artefatos da Camada 2.

Lê ``metadados_processados.csv``, carrega os vetores MFCC persistidos e monta
as estruturas usadas pela Camada 3:

* ``X`` — descritores de 60 dimensões, um por segmento;
* ``X_energia`` — energia espectral na banda diagnóstica, usada pelo baseline;
* ``y`` — rótulo binário (0 normal, 1 anomalia);
* ``grupos`` — identificador da unidade, para ``leave-one-unit-out``;
* ``gravacoes`` — identificador da gravação, para ``leave-one-recording-out``
  e para a agregação da decisão em nível de gravação.

Os segmentos rotulados como ``standby`` e ``referencia`` são preservados no
conjunto de dados, mas ficam fora da coorte binária: o standby é um regime
transitório e a referência é, por definição, o que se quer remover do sinal.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from noisedc.features.descriptors import descritor_60d

log = logging.getLogger(__name__)

ROTULOS_BINARIOS = {"normal": 0, "anomalia": 1}


@dataclass
class Coorte:
    """Conjunto pronto para a Camada 3."""

    X: np.ndarray
    X_energia: np.ndarray
    y: np.ndarray
    grupos: np.ndarray
    gravacoes: np.ndarray
    metadados: pd.DataFrame

    def __len__(self) -> int:
        return len(self.y)

    def resumo(self) -> str:
        unidades = sorted(set(self.grupos))
        unidades_anomalas = sorted(set(self.grupos[self.y == 1]))
        return (
            f"{len(self)} segmentos | {int((self.y == 0).sum())} normais, "
            f"{int((self.y == 1).sum())} anômalos | "
            f"{len(set(self.gravacoes))} gravações | "
            f"{len(unidades)} unidades ({', '.join(unidades)}) | "
            f"anomalia em: {', '.join(unidades_anomalas) or 'nenhuma'}"
        )


def carregar_coorte(
    caminho_metadados: str | Path,
    *,
    raiz_artefatos: str | Path | None = None,
    n_mfcc: int = 20,
    apenas_binaria: bool = True,
) -> Coorte:
    """Carrega a coorte de classificação.

    Parameters
    ----------
    caminho_metadados
        Caminho de ``metadados_processados.csv``.
    raiz_artefatos
        Diretório a partir do qual os caminhos relativos dos ``.npy`` são
        resolvidos. Por padrão, a pasta do próprio arquivo de metadados.
    apenas_binaria
        Mantém somente os segmentos ``normal`` e ``anomalia``.
    """
    caminho_metadados = Path(caminho_metadados)
    if not caminho_metadados.exists():
        raise FileNotFoundError(
            f"Metadados não encontrados: {caminho_metadados}\n"
            "Execute antes:  python -m noisedc.preprocessing.run"
        )

    raiz = Path(raiz_artefatos) if raiz_artefatos else caminho_metadados.parent
    tabela = pd.read_csv(caminho_metadados)

    obrigatorias = {"equipamento", "estado", "caminho_mfcc", "arquivo_origem"}
    faltantes = obrigatorias - set(tabela.columns)
    if faltantes:
        raise ValueError(f"Colunas ausentes em {caminho_metadados.name}: {sorted(faltantes)}")

    tabela["estado"] = tabela["estado"].astype(str).str.strip().str.lower()

    if apenas_binaria:
        antes = len(tabela)
        tabela = tabela[tabela["estado"].isin(ROTULOS_BINARIOS)].copy()
        if len(tabela) < antes:
            log.info(
                "%d segmentos fora da coorte binária (standby/referência) foram preservados "
                "no conjunto, mas excluídos da avaliação.",
                antes - len(tabela),
            )

    if tabela.empty:
        raise ValueError("Nenhum segmento rotulado como 'normal' ou 'anomalia' encontrado.")

    descritores: list[np.ndarray] = []
    linhas_validas: list[int] = []
    for posicao, linha in tabela.reset_index(drop=True).iterrows():
        caminho = raiz / str(linha["caminho_mfcc"])
        if not caminho.exists():
            log.warning("Vetor MFCC ausente, segmento ignorado: %s", caminho)
            continue
        descritores.append(descritor_60d(np.load(caminho), n_mfcc=n_mfcc))
        linhas_validas.append(posicao)

    if not descritores:
        raise RuntimeError(
            "Nenhum vetor MFCC pôde ser carregado. Verifique se 'raiz_artefatos' "
            "aponta para o diretório correto."
        )

    tabela = tabela.reset_index(drop=True).iloc[linhas_validas].reset_index(drop=True)

    energia = (
        tabela["energia_banda"].to_numpy(dtype=float).reshape(-1, 1)
        if "energia_banda" in tabela.columns
        else np.zeros((len(tabela), 1))
    )
    if "energia_banda" not in tabela.columns:
        log.warning(
            "Coluna 'energia_banda' ausente: o baseline não terá característica de entrada. "
            "Reexecute a Camada 2 para gerá-la."
        )

    return Coorte(
        X=np.vstack(descritores),
        X_energia=energia,
        y=tabela["estado"].map(ROTULOS_BINARIOS).to_numpy(dtype=int),
        grupos=tabela["equipamento"].astype(str).to_numpy(),
        gravacoes=tabela["arquivo_origem"].astype(str).to_numpy(),
        metadados=tabela,
    )
