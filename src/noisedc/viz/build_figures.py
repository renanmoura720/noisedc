"""Geração das figuras a partir dos artefatos de avaliação.

Lê ``results/metrics/`` e produz as figuras em ``results/figures/``. Nenhuma
figura é desenhada a partir de números digitados manualmente: toda imagem é
derivada dos CSV gerados pela Camada 3, de modo que reexecutar o pipeline
atualiza texto, tabelas e figuras de forma consistente.

Uso::

    python -m noisedc.viz.build_figures
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from noisedc.config import RAIZ_PROJETO  # noqa: E402
from noisedc.models.registry import ROTULOS_LEGIVEIS  # noqa: E402

log = logging.getLogger(__name__)

plt.rcParams.update(
    {
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "font.size": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linewidth": 0.5,
    }
)

COR_NORMAL = "#2a7f8f"
COR_ANOMALIA = "#b3283a"


def figura_matriz_confusao(caminho_csv: Path, destino: Path) -> Path:
    """Matriz de confusão com contagens e percentuais por linha."""
    matriz = pd.read_csv(caminho_csv, index_col=0)
    valores = matriz.to_numpy(dtype=float)
    percentuais = valores / np.maximum(valores.sum(axis=1, keepdims=True), 1) * 100

    figura, eixo = plt.subplots(figsize=(4.2, 3.6))
    imagem = eixo.imshow(percentuais, cmap="Blues", vmin=0, vmax=100)

    for i in range(valores.shape[0]):
        for j in range(valores.shape[1]):
            eixo.text(
                j, i,
                f"{int(valores[i, j])}\n{percentuais[i, j]:.1f}%",
                ha="center", va="center",
                color="white" if percentuais[i, j] > 55 else "#1c2229",
                fontsize=9,
            )

    eixo.set_xticks(range(matriz.shape[1]), matriz.columns, fontsize=8)
    eixo.set_yticks(range(matriz.shape[0]), matriz.index, fontsize=8)
    eixo.grid(False)
    eixo.set_title(caminho_csv.stem.replace("matriz_confusao__", "").replace("__", " · "),
                   fontsize=9)
    figura.colorbar(imagem, ax=eixo, label="% da classe real", fraction=0.046)
    figura.tight_layout()

    destino.parent.mkdir(parents=True, exist_ok=True)
    figura.savefig(destino, bbox_inches="tight")
    plt.close(figura)
    return destino


def figura_comparativo(caminho_csv: Path, destino: Path) -> Path:
    """Comparação dos métodos por protocolo, em barras agrupadas."""
    tabela = pd.read_csv(caminho_csv)
    metricas = ["recall", "precisao", "f1", "auc"]
    protocolos = tabela["protocolo"].unique()

    figura, eixos = plt.subplots(
        1, len(protocolos), figsize=(5.2 * len(protocolos), 3.6), squeeze=False
    )

    for coluna, protocolo in enumerate(protocolos):
        eixo = eixos[0][coluna]
        recorte = tabela[tabela["protocolo"] == protocolo]
        metodos = recorte["metodo"].tolist()
        posicoes = np.arange(len(metodos))
        largura = 0.8 / len(metricas)

        for i, metrica in enumerate(metricas):
            eixo.bar(
                posicoes + i * largura - 0.4 + largura / 2,
                recorte[metrica].to_numpy(),
                width=largura,
                label=metrica.upper() if metrica == "auc" else metrica.capitalize(),
            )

        eixo.set_xticks(posicoes)
        eixo.set_xticklabels(
            [ROTULOS_LEGIVEIS.get(m, m).replace(" (", "\n(") for m in metodos], fontsize=7.5
        )
        eixo.set_ylim(0, 1.0)
        eixo.set_title(protocolo, fontsize=9)
        if coluna == 0:
            eixo.set_ylabel("valor da métrica")
            eixo.legend(fontsize=7.5, ncols=2, frameon=False)

    figura.tight_layout()
    destino.parent.mkdir(parents=True, exist_ok=True)
    figura.savefig(destino, bbox_inches="tight")
    plt.close(figura)
    return destino


def figura_desempenho_por_unidade(caminho_csv: Path, destino: Path) -> Path:
    """Recall e AUC por unidade sob validação por unidade.

    Torna visível a dispersão entre equipamentos, que a média entre dobras
    esconde — e é justamente essa dispersão que responde à pergunta sobre
    generalização.
    """
    tabela = pd.read_csv(caminho_csv)
    if "particao" not in tabela.columns:
        raise ValueError(f"{caminho_csv.name} não contém a coluna 'particao'")

    tabela = tabela.sort_values("particao")
    posicoes = np.arange(len(tabela))

    figura, eixo = plt.subplots(figsize=(6.0, 3.4))
    eixo.bar(posicoes - 0.2, tabela["recall"], width=0.4, label="Recall", color=COR_ANOMALIA)
    eixo.bar(posicoes + 0.2, tabela["auc"], width=0.4, label="AUC", color=COR_NORMAL)

    eixo.axhline(0.5, color="#6b7684", linestyle="--", linewidth=0.8)
    eixo.text(len(tabela) - 0.5, 0.52, "acaso", fontsize=7, color="#6b7684", ha="right")

    eixo.set_xticks(posicoes)
    eixo.set_xticklabels(tabela["particao"], fontsize=8)
    eixo.set_ylim(0, 1.0)
    eixo.set_ylabel("valor da métrica")
    eixo.set_xlabel("unidade reservada para teste")
    eixo.legend(fontsize=8, frameon=False)
    figura.tight_layout()

    destino.parent.mkdir(parents=True, exist_ok=True)
    figura.savefig(destino, bbox_inches="tight")
    plt.close(figura)
    return destino


def executar(metricas: Path, figuras: Path) -> list[Path]:
    """Gera todas as figuras derivadas dos artefatos disponíveis."""
    figuras.mkdir(parents=True, exist_ok=True)
    geradas: list[Path] = []

    for caminho in sorted(metricas.glob("matriz_confusao__*.csv")):
        destino = figuras / f"{caminho.stem}.png"
        geradas.append(figura_matriz_confusao(caminho, destino))
        log.info("figura: %s", destino.name)

    comparativo = metricas / "comparativo_metodos.csv"
    if comparativo.exists():
        destino = figuras / "comparativo_metodos.png"
        geradas.append(figura_comparativo(comparativo, destino))
        log.info("figura: %s", destino.name)

    for caminho in sorted(metricas.glob("metricas__*__leave-one-unit-out.csv")):
        metodo = caminho.stem.split("__")[1]
        destino = figuras / f"desempenho_por_unidade__{metodo}.png"
        try:
            geradas.append(figura_desempenho_por_unidade(caminho, destino))
            log.info("figura: %s", destino.name)
        except ValueError as erro:
            log.warning("  %s", erro)

    if not geradas:
        log.warning(
            "Nenhuma figura gerada. Execute antes:  python -m noisedc.evaluation.run"
        )
    return geradas


def principal(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Geração das figuras")
    parser.add_argument("--metricas", default=None)
    parser.add_argument("--figuras", default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    executar(
        Path(args.metricas or RAIZ_PROJETO / "results" / "metrics"),
        Path(args.figuras or RAIZ_PROJETO / "results" / "figures"),
    )
    return 0


if __name__ == "__main__":
    sys.exit(principal())
