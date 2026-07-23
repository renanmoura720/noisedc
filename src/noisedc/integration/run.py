"""Camada 4 — classificação de novas gravações e publicação dos eventos.

Fecha a cadeia: recebe áudio, aplica o pipeline da Camada 2, classifica com o
modelo persistido pela Camada 3, consolida a decisão por gravação e publica o
resultado no Zabbix.

Executa em **modo de simulação por padrão**. O envio efetivo exige a opção
``--enviar`` e um ``.env`` preenchido, de modo que ninguém dispare alertas em
um ambiente de produção por engano ao seguir o README.

Uso::

    python -m noisedc.integration.run --audio data/raw/EV11/2026-03-12_1430_normal.wav
    python -m noisedc.integration.run --audio ... --modelo results/models/svm.joblib --enviar
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import joblib
import numpy as np

from noisedc.config import RAIZ_PROJETO, Config, variavel_de_ambiente
from noisedc.features.descriptors import descritor_60d
from noisedc.features.extract import ParametrosExtracao, mfcc_com_deltas
from noisedc.integration.zabbix import ClienteZabbix, Evento, escrever_lote
from noisedc.preprocessing.audio import carregar_audio, normalizar_rms
from noisedc.preprocessing.segmentation import segmentar
from noisedc.preprocessing.spectral_subtraction import aplicar_com_referencia

log = logging.getLogger(__name__)


def classificar_gravacao(
    caminho_audio: Path,
    modelo,
    config: Config,
    *,
    caminho_referencia: Path | None = None,
) -> tuple[int, float, int]:
    """Classifica uma gravação inteira.

    A decisão operacional é consolidada em nível de gravação, e não de
    segmento: com janelas de 2 s sobrepostas em 50%, um único segmento
    positivo é evidência fraca, e alertar a cada um deles produziria o tipo de
    ruído que faz uma equipe desligar as notificações.

    Returns
    -------
    (estado, confianca, n_segmentos)
    """
    p = ParametrosExtracao.da_config(config)
    rms_alvo = float(config.obter("preprocessamento.normalizacao_rms_alvo", 0.1))

    sinal, taxa = carregar_audio(caminho_audio, taxa_alvo=p.taxa)
    referencia = None
    if caminho_referencia and Path(caminho_referencia).exists():
        referencia, _ = carregar_audio(caminho_referencia, taxa_alvo=p.taxa)
        referencia = normalizar_rms(referencia, alvo=rms_alvo)

    sinal = normalizar_rms(sinal, alvo=rms_alvo)
    sinal = aplicar_com_referencia(sinal, referencia, n_fft=p.n_fft, hop_length=p.hop_length)
    sinal = normalizar_rms(sinal, alvo=rms_alvo)

    segmentos = segmentar(
        sinal,
        taxa,
        janela_s=float(config.obter("preprocessamento.segmentacao.janela_s", 2.0)),
        sobreposicao=float(config.obter("preprocessamento.segmentacao.sobreposicao", 0.5)),
    )
    if not segmentos:
        raise ValueError(f"Gravação curta demais para segmentar: {caminho_audio}")

    X = np.vstack([descritor_60d(mfcc_com_deltas(s.sinal, p), n_mfcc=p.n_mfcc) for s in segmentos])

    predito = modelo.predict(X)
    fracao_anomala = float(np.mean(predito == 1))

    estado = int(fracao_anomala > 0.5)
    confianca = fracao_anomala if estado == 1 else 1.0 - fracao_anomala

    return estado, confianca, len(segmentos)


def principal(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Camada 4 — classificação e publicação")
    parser.add_argument("--audio", required=True, help="arquivo .wav a classificar")
    parser.add_argument("--referencia", default=None, help="gravação de referência da sessão")
    parser.add_argument("--modelo", default=None, help="modelo .joblib a utilizar")
    parser.add_argument("--equipamento", default=None, help="host no Zabbix (ex.: EV11)")
    parser.add_argument("--config", default=None)
    parser.add_argument(
        "--enviar",
        action="store_true",
        help="envia de fato ao Zabbix; sem esta opção, apenas simula",
    )
    parser.add_argument("--lote", default=None, help="grava o arquivo de lote do zabbix_sender")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    config = Config.carregar(args.config)

    caminho_audio = Path(args.audio)
    caminho_modelo = Path(args.modelo or RAIZ_PROJETO / "results" / "models" / "svm.joblib")
    if not caminho_modelo.exists():
        raise FileNotFoundError(
            f"Modelo não encontrado: {caminho_modelo}\n"
            "Treine antes com:  python -m noisedc.models.train"
        )

    modelo = joblib.load(caminho_modelo)
    equipamento = args.equipamento or caminho_audio.parent.name

    estado, confianca, n_segmentos = classificar_gravacao(
        caminho_audio,
        modelo,
        config,
        caminho_referencia=Path(args.referencia) if args.referencia else None,
    )

    evento = Evento(
        equipamento=equipamento,
        estado=estado,
        confianca=confianca,
        arquivo_audio=caminho_audio.name,
        dispositivo=variavel_de_ambiente("DISPOSITIVO_ID", "") or "",
    )

    limiar = float(config.obter("integracao.confianca_minima", 0.80))
    log.info(json.dumps(evento.como_dicionario(), ensure_ascii=False, indent=2))
    log.info(
        "%d segmentos analisados | severidade: %s",
        n_segmentos,
        evento.severidade(confianca_minima=limiar),
    )

    if args.lote:
        destino = escrever_lote([evento], args.lote)
        log.info("Arquivo de lote gravado em %s", destino)

    cliente = ClienteZabbix(simular=not args.enviar)
    cliente.enviar_evento(evento)

    if not args.enviar:
        log.info(
            "\nModo de simulação: nada foi enviado. Use --enviar com o .env preenchido "
            "para publicar de fato."
        )
    return 0


if __name__ == "__main__":
    sys.exit(principal())
