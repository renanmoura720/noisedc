#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Camada 4 — reconstrução do script de integração com o Zabbix (Linha C, EV09-EV14).

⚠️  RECONSTRUÇÃO, NÃO O ORIGINAL. Escrito a partir da descrição textual da
    Seção 5.2.4 da dissertação (itens trapper `acustico.estado` e
    `acustico.confianca`, envio via `zabbix_sender`, severidades por
    patamar de confiança) e da nomenclatura real EV09-EV14 confirmada pelos
    dados. Não há número desta camada para validar contra o texto — ao
    contrário da Camada 3, a integração não produz métricas reportadas em
    tabela, então este script não passou pelo mesmo processo de verificação
    numérica. Trate como ponto de partida.

Fluxo: para cada gravação já classificada pela Camada 3 (estado + confiança
por segmento), consolida a decisão em nível de gravação por voto majoritário
— a mesma regra usada em camada3_autoritativo_linha_c.py, seção [2] — e envia
os dois itens trapper ao host correspondente da evaporadora.

Entrada esperada: um CSV com pelo menos as colunas
  sample_id, evaporadora, y_pred (0/1), score (confiança em [0,1])
produzido por um passo de inferência sobre features_segmentos.csv com o
modelo já treinado (ver src/noisedc/models/train.py para o pipeline
modular equivalente).

Uso:
    python reconstrucao_camada4_integracao_zabbix.py --enviar
    python reconstrucao_camada4_integracao_zabbix.py   # modo simulação (padrão)
"""
from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ITEM_ESTADO = "acustico.estado"
ITEM_CONFIANCA = "acustico.confianca"
PREFIXO_HOST = "EV"  # host no Zabbix: EV09, EV10, ..., EV14

CONFIANCA_MINIMA = 0.80  # abaixo disso, severidade "aviso" mesmo se estado=1
CONFIANCA_ALTA = 0.95    # acima disso, severidade "alto"

ENTRADA = Path("dataset_linhaC/04_resultados/predicoes_segmentos.csv")


@dataclass
class DecisaoGravacao:
    evaporadora: int
    sample_id: str
    estado: int       # 0 normal, 1 anômalo — voto majoritário dos segmentos
    confianca: float  # média dos escores dos segmentos da gravação

    @property
    def host(self) -> str:
        return f"{PREFIXO_HOST}{self.evaporadora:02d}"

    def severidade(self) -> str:
        if self.estado == 0:
            return "informativo"
        if self.confianca < CONFIANCA_MINIMA:
            return "aviso"
        if self.confianca < CONFIANCA_ALTA:
            return "medio"
        return "alto"


def consolidar_por_gravacao(caminho_predicoes: Path) -> list[DecisaoGravacao]:
    """Agrega predições por segmento em decisão por gravação (voto majoritário).

    Mesma regra de camada3_autoritativo_linha_c.py: uma gravação é sinalizada
    quando a fração de segmentos positivos é >= 0,5. A sobreposição de 50%
    entre segmentos torna a decisão por segmento isolado pouco confiável; em
    nível de gravação ela é irrelevante.
    """
    por_gravacao_pred: dict[str, list[int]] = defaultdict(list)
    por_gravacao_score: dict[str, list[float]] = defaultdict(list)
    evaporadora_por_gravacao: dict[str, int] = {}

    with caminho_predicoes.open(encoding="utf-8", newline="") as f:
        for linha in csv.DictReader(f):
            sid = linha["sample_id"]
            por_gravacao_pred[sid].append(int(linha["y_pred"]))
            por_gravacao_score[sid].append(float(linha["score"]))
            evaporadora_por_gravacao[sid] = int(linha["evaporadora"])

    decisoes = []
    for sid in sorted(por_gravacao_pred):
        preds = por_gravacao_pred[sid]
        estado = int((sum(preds) / len(preds)) >= 0.5)
        confianca = sum(por_gravacao_score[sid]) / len(por_gravacao_score[sid])
        decisoes.append(
            DecisaoGravacao(
                evaporadora=evaporadora_por_gravacao[sid],
                sample_id=sid,
                estado=estado,
                confianca=confianca,
            )
        )
    return decisoes


def montar_comando_sender(
    caminho_sender: str, servidor: str, porta: int, host: str, chave: str, valor: str
) -> list[str]:
    return [caminho_sender, "-z", servidor, "-p", str(porta), "-s", host, "-k", chave, "-o", valor]


def enviar(decisoes: list[DecisaoGravacao], *, servidor: str, porta: int, simular: bool) -> None:
    caminho_sender = shutil.which("zabbix_sender") or "zabbix_sender"

    for d in decisoes:
        comandos = [
            montar_comando_sender(caminho_sender, servidor, porta, d.host, ITEM_ESTADO, str(d.estado)),
            montar_comando_sender(
                caminho_sender, servidor, porta, d.host, ITEM_CONFIANCA, f"{d.confianca:.4f}"
            ),
        ]
        print(
            f"{d.host}  {d.sample_id:42s}  estado={d.estado}  "
            f"confianca={d.confianca:.3f}  severidade={d.severidade()}"
        )
        for comando in comandos:
            if simular:
                print(f"  [simulação] {' '.join(comando)}")
                continue
            resultado = subprocess.run(comando, capture_output=True, text=True, timeout=30)
            if resultado.returncode != 0:
                print(f"  ERRO ao enviar para {d.host}: {resultado.stderr.strip()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Camada 4 — envio ao Zabbix (reconstrução)")
    parser.add_argument("--entrada", default=str(ENTRADA))
    parser.add_argument("--servidor", default="<ZABBIX_SERVER>", help="endereço do servidor Zabbix")
    parser.add_argument("--porta", type=int, default=10051)
    parser.add_argument(
        "--enviar", action="store_true", help="envia de fato; sem esta opção, apenas simula"
    )
    args = parser.parse_args()

    caminho = Path(args.entrada)
    if not caminho.exists():
        raise SystemExit(
            f"Arquivo de predições não encontrado: {caminho}\n"
            "Gere-o a partir de features_segmentos.csv com um modelo treinado "
            "(colunas mínimas: sample_id, evaporadora, y_pred, score)."
        )

    decisoes = consolidar_por_gravacao(caminho)
    print(f"{len(decisoes)} gravações consolidadas\n")

    enviar(decisoes, servidor=args.servidor, porta=args.porta, simular=not args.enviar)

    if not args.enviar:
        print("\nModo de simulação: nada foi enviado. Use --enviar com --servidor real para publicar.")


if __name__ == "__main__":
    main()
