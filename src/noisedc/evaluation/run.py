"""Camada 3 — avaliação dos métodos sob os protocolos de validação.

Executa cada método em cada partição, em nível de segmento e de gravação, e
persiste métricas, matrizes de confusão e resultados por unidade em
``results/metrics/``.

Uso::

    python -m noisedc.evaluation.run --protocol leave-one-unit-out
    python -m noisedc.evaluation.run --protocol leave-one-recording-out
    python -m noisedc.evaluation.run --protocol todos --metodo svm
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from noisedc.config import RAIZ_PROJETO, Config
from noisedc.dataset import Coorte, carregar_coorte
from noisedc.evaluation.metrics import (
    agregar_por_gravacao,
    calcular_metricas,
    consolidar,
    matriz_de_confusao,
)
from noisedc.evaluation.protocols import PROTOCOLOS, descrever_particao, particoes
from noisedc.models.registry import METODOS, ROTULOS_LEGIVEIS, criar_modelo, usa_apenas_energia

log = logging.getLogger(__name__)


def avaliar_metodo(
    metodo: str,
    coorte: Coorte,
    protocolo: str,
    config: Config,
) -> tuple[pd.DataFrame, pd.DataFrame, dict, dict]:
    """Avalia um método sob um protocolo, em todas as partições.

    Duas leituras complementares são produzidas:

    * **por partição** — permite examinar a dispersão entre unidades, que é o
      que responde à pergunta sobre generalização; sob
      ``leave-one-recording-out``, dobras de classe única têm AUC indefinida e
      aparecem como ``NaN``;
    * **agregada** — reúne as predições de todas as dobras antes de calcular as
      métricas. É o número comparável entre protocolos e o que corresponde à
      matriz de confusão reportada.

    Returns
    -------
    (metricas_por_particao, matriz_de_confusao, metricas_agregadas, metricas_por_gravacao)
    """
    X = coorte.X_energia if usa_apenas_energia(metodo) else coorte.X

    linhas: list[dict] = []
    y_todos: list[np.ndarray] = []
    predito_todos: list[np.ndarray] = []
    escore_todos: list[np.ndarray] = []
    gravacao_todas: list[np.ndarray] = []

    for nome, treino, teste in particoes(protocolo, coorte.y, coorte.grupos, coorte.gravacoes):
        classes_no_treino = np.unique(coorte.y[treino])
        if len(classes_no_treino) < 2 and metodo != "one_class_svm":
            log.debug(
                "  partição '%s' ignorada para %s: treino com uma única classe.", nome, metodo
            )
            continue

        modelo = criar_modelo(metodo, config)
        modelo.fit(X[treino], coorte.y[treino])

        escores = modelo.decision_function(X[teste])
        predito = modelo.predict(X[teste])

        metricas = calcular_metricas(coorte.y[teste], predito, escores)
        metricas.update(
            {
                "metodo": metodo,
                "protocolo": protocolo,
                "nivel": "segmento",
                "particao": nome,
                **descrever_particao(coorte.y, treino, teste),
            }
        )
        linhas.append(metricas)

        y_todos.append(coorte.y[teste])
        predito_todos.append(predito)
        escore_todos.append(escores)
        gravacao_todas.append(coorte.gravacoes[teste])

    if not linhas:
        log.warning("  nenhuma partição avaliável para %s sob %s", metodo, protocolo)
        return pd.DataFrame(), pd.DataFrame(), {}, {}

    y_concat = np.concatenate(y_todos)
    predito_concat = np.concatenate(predito_todos)
    escore_concat = np.concatenate(escore_todos)
    gravacao_concat = np.concatenate(gravacao_todas)

    matriz = matriz_de_confusao(y_concat, predito_concat)

    agregadas = calcular_metricas(y_concat, predito_concat, escore_concat)
    agregadas.update(
        {
            "metodo": metodo,
            "protocolo": protocolo,
            "nivel": "segmento",
            "particao": "AGREGADO",
            "n_particoes": len(linhas),
            "n_segmentos": int(len(y_concat)),
        }
    )

    rotulos_grav, escores_grav, predicoes_grav, _ = agregar_por_gravacao(
        gravacao_concat, y_concat, escore_concat, predito_concat
    )
    por_gravacao = calcular_metricas(rotulos_grav, predicoes_grav, escores_grav)
    por_gravacao.update(
        {
            "metodo": metodo,
            "protocolo": protocolo,
            "nivel": "gravacao",
            "particao": "AGREGADO",
            "n_gravacoes": int(len(rotulos_grav)),
        }
    )

    return pd.DataFrame(linhas), matriz, agregadas, por_gravacao


def executar(
    coorte: Coorte,
    config: Config,
    protocolos: list[str],
    metodos: list[str],
    saida: Path,
) -> pd.DataFrame:
    """Executa a avaliação completa e persiste os artefatos."""
    saida.mkdir(parents=True, exist_ok=True)

    por_particao: list[pd.DataFrame] = []
    agregadas: list[dict] = []
    por_gravacao: list[dict] = []

    for protocolo in protocolos:
        log.info("Protocolo: %s", protocolo)
        for metodo in metodos:
            log.info("  método: %s", ROTULOS_LEGIVEIS.get(metodo, metodo))
            tabela, matriz, agregada, gravacao = avaliar_metodo(metodo, coorte, protocolo, config)
            if tabela.empty:
                continue

            por_particao.append(tabela)
            agregadas.append(agregada)
            por_gravacao.append(gravacao)

            sufixo = f"{metodo}__{protocolo}"
            tabela.to_csv(saida / f"metricas__{sufixo}.csv", index=False)
            matriz.to_csv(saida / f"matriz_confusao__{sufixo}.csv")
            consolidar(tabela.to_dict("records")).to_csv(
                saida / f"resumo__{sufixo}.csv", index=False
            )

            log.info(
                "    segmento: recall %.3f | F1 %.3f | AUC %.3f | TFP %.3f   "
                "(%d dobras, %d segmentos)",
                agregada["recall"], agregada["f1"], agregada["auc"],
                agregada["taxa_falsos_positivos"], agregada["n_particoes"],
                agregada["n_segmentos"],
            )
            log.info(
                "    gravação: recall %.3f | F1 %.3f | AUC %.3f   (%d gravações)",
                gravacao["recall"], gravacao["f1"], gravacao["auc"], gravacao["n_gravacoes"],
            )

    if not por_particao:
        raise RuntimeError("Nenhuma avaliação pôde ser concluída.")

    pd.concat(por_particao, ignore_index=True).to_csv(
        saida / "metricas_por_particao.csv", index=False
    )
    pd.DataFrame(por_gravacao).to_csv(saida / "metricas_por_gravacao.csv", index=False)

    comparativo = pd.DataFrame(agregadas)[
        ["protocolo", "metodo", "recall", "precisao", "f1", "auc",
         "taxa_falsos_positivos", "n_particoes", "n_segmentos"]
    ].round(3)
    comparativo.to_csv(saida / "comparativo_metodos.csv", index=False)

    (saida / "resumo_execucao.json").write_text(
        json.dumps(
            {
                "coorte": coorte.resumo(),
                "protocolos": protocolos,
                "metodos": metodos,
                "observacao": (
                    "As métricas agregadas reúnem as predições de todas as dobras. "
                    "As métricas por partição, em metricas_por_particao.csv, mostram a "
                    "dispersão entre unidades — sob leave-one-unit-out, é essa dispersão "
                    "que responde à pergunta sobre generalização."
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    log.info("\n%s", comparativo.to_string(index=False))
    log.info("\nArtefatos gravados em %s", saida)
    return comparativo


def principal(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Camada 3 — avaliação dos métodos")
    parser.add_argument("--config", default=None)
    parser.add_argument(
        "--protocol",
        default="todos",
        choices=[*PROTOCOLOS, "todos"],
        help="protocolo de validação",
    )
    parser.add_argument(
        "--metodo",
        default="todos",
        choices=[*METODOS, "todos"],
        help="método a avaliar",
    )
    parser.add_argument("--metadados", default=None)
    parser.add_argument("--saida", default=None)
    parser.add_argument("--verboso", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verboso else logging.INFO, format="%(message)s"
    )

    config = Config.carregar(args.config)
    metadados = Path(
        args.metadados or RAIZ_PROJETO / "data" / "processed" / "metadados_processados.csv"
    )
    saida = Path(args.saida or RAIZ_PROJETO / "results" / "metrics")

    coorte = carregar_coorte(metadados, n_mfcc=int(config.obter("caracteristicas.n_mfcc", 20)))
    log.info("Coorte: %s", coorte.resumo())

    protocolos = list(PROTOCOLOS) if args.protocol == "todos" else [args.protocol]
    metodos = list(METODOS) if args.metodo == "todos" else [args.metodo]

    executar(coorte, config, protocolos, metodos, saida)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
