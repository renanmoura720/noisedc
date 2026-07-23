"""Camada 3 — treinamento dos modelos finais.

A avaliação (``noisedc.evaluation.run``) treina e descarta um modelo por
partição, porque seu objetivo é estimar desempenho. Este módulo faz outra
coisa: treina sobre **todo** o conjunto disponível e persiste o modelo que a
Camada 4 usará em operação.

A distinção importa. O modelo de produção nunca deve ser aquele de uma dobra
específica da validação, e o desempenho de produção nunca deve ser estimado
pelo desempenho no conjunto em que o modelo foi treinado.

Uso::

    python -m noisedc.models.train --config configs/config.yaml
    python -m noisedc.models.train --metodo floresta_aleatoria
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np

from noisedc.config import RAIZ_PROJETO, Config
from noisedc.dataset import carregar_coorte
from noisedc.features.descriptors import nomes_das_dimensoes
from noisedc.models.registry import METODOS, ROTULOS_LEGIVEIS, criar_modelo, usa_apenas_energia

log = logging.getLogger(__name__)


def treinar(metodo: str, coorte, config: Config):
    """Treina um método sobre a coorte completa."""
    X = coorte.X_energia if usa_apenas_energia(metodo) else coorte.X
    modelo = criar_modelo(metodo, config)
    modelo.fit(X, coorte.y)
    return modelo


def importancia_de_atributos(modelo, n_mfcc: int = 20) -> dict[str, float] | None:
    """Extrai a importância das características, quando o método a fornece.

    Disponível na Floresta Aleatória, é o que permite identificar quais
    coeficientes MFCC mais contribuem para a discriminação — informação de
    interpretação, não apenas de desempenho.
    """
    interno = getattr(modelo, "estimador_", modelo)
    importancias = getattr(interno, "feature_importances_", None)
    if importancias is None:
        return None

    nomes = nomes_das_dimensoes(n_mfcc)
    if len(nomes) != len(importancias):
        nomes = [f"dim{i}" for i in range(len(importancias))]

    pares = sorted(zip(nomes, importancias, strict=True), key=lambda par: par[1], reverse=True)
    return {nome: float(valor) for nome, valor in pares}


def executar(metodos: list[str], coorte, config: Config, saida: Path) -> list[Path]:
    saida.mkdir(parents=True, exist_ok=True)
    gerados: list[Path] = []

    for metodo in metodos:
        log.info("Treinando: %s", ROTULOS_LEGIVEIS.get(metodo, metodo))
        modelo = treinar(metodo, coorte, config)

        destino = saida / f"{metodo}.joblib"
        joblib.dump(modelo, destino)
        gerados.append(destino)

        ficha = {
            "metodo": metodo,
            "rotulo": ROTULOS_LEGIVEIS.get(metodo, metodo),
            "treinado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "n_segmentos": int(len(coorte)),
            "n_normais": int((coorte.y == 0).sum()),
            "n_anomalos": int((coorte.y == 1).sum()),
            "unidades": sorted(set(coorte.grupos.tolist())),
            "dimensao_entrada": 1 if usa_apenas_energia(metodo) else int(coorte.X.shape[1]),
            "seed": int(config.obter("projeto.seed", 42)),
        }

        importancias = importancia_de_atributos(
            modelo, n_mfcc=int(config.obter("caracteristicas.n_mfcc", 20))
        )
        if importancias:
            ficha["atributos_mais_importantes"] = dict(list(importancias.items())[:10])

        if hasattr(modelo, "limiar_"):
            ficha["limiar_ajustado"] = float(modelo.limiar_)
            ficha["f1_no_treino"] = float(modelo.f1_treino_)

        (saida / f"{metodo}.json").write_text(
            json.dumps(ficha, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        log.info("  modelo salvo em %s", destino)

    return gerados


def principal(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Camada 3 — treinamento dos modelos finais")
    parser.add_argument("--config", default=None)
    parser.add_argument("--metodo", default="todos", choices=[*METODOS, "todos"])
    parser.add_argument("--metadados", default=None)
    parser.add_argument("--saida", default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    config = Config.carregar(args.config)
    np.random.seed(int(config.obter("projeto.seed", 42)))

    metadados = Path(
        args.metadados or RAIZ_PROJETO / "data" / "processed" / "metadados_processados.csv"
    )
    saida = Path(args.saida or RAIZ_PROJETO / "results" / "models")

    coorte = carregar_coorte(metadados, n_mfcc=int(config.obter("caracteristicas.n_mfcc", 20)))
    log.info("Coorte: %s", coorte.resumo())

    metodos = list(METODOS) if args.metodo == "todos" else [args.metodo]
    executar(metodos, coorte, config, saida)

    log.info(
        "\nAtenção: estes modelos foram treinados sobre todo o conjunto e destinam-se "
        "à operação (Camada 4). Para estimativas de desempenho, use "
        "'python -m noisedc.evaluation.run'."
    )
    return 0


if __name__ == "__main__":
    sys.exit(principal())
