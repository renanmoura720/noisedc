"""Camada 2 — execução do pipeline de pré-processamento.

Percorre ``data/raw/``, aplica a sequência descrita na dissertação e persiste
os artefatos por segmento junto com os metadados de proveniência:

1. padronização para 22.050 Hz, mono, 16 bits;
2. normalização de amplitude por RMS (alvo 0,1);
3. subtração espectral usando a gravação de referência;
4. nova normalização RMS;
5. segmentação em janelas de 2 s com 50% de sobreposição;
6. extração de STFT, Mel e MFCC + deltas.

Como os arquivos brutos e as referências são preservados, o pipeline pode ser
reexecutado com parâmetros distintos sobre o mesmo material, sem nova coleta.

Uso::

    python -m noisedc.preprocessing.run --config configs/config.yaml
    python -m noisedc.preprocessing.run --entrada data/raw --saida data/processed
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

import numpy as np

from noisedc.config import RAIZ_PROJETO, Config
from noisedc.features.extract import (
    ParametrosExtracao,
    energia_espectral_banda,
    espectrograma_mel_db,
    espectrograma_stft_db,
    mfcc_com_deltas,
    salvar_espectrograma,
)
from noisedc.preprocessing.audio import carregar_audio, normalizar_rms
from noisedc.preprocessing.segmentation import segmentar
from noisedc.preprocessing.spectral_subtraction import aplicar_com_referencia

log = logging.getLogger(__name__)

COLUNAS_METADADOS = [
    "arquivo_origem",
    "indice_segmento",
    "equipamento",
    "estado",
    "sessao_coleta",
    "inicio_s",
    "usou_referencia",
    "energia_banda",
    "caminho_stft",
    "caminho_mel",
    "caminho_mfcc",
]

ESTADOS_CONHECIDOS = {"normal", "anomalia", "standby", "referencia"}


def descobrir_gravacoes(entrada: Path) -> list[dict]:
    """Localiza as gravações e associa cada uma à sua referência.

    Duas convenções são aceitas, nessa ordem de precedência:

    * um ``metadados.csv`` dentro da pasta da unidade, com as colunas
      ``arquivo``, ``estado`` e, opcionalmente, ``referencia`` e
      ``sessao_coleta``;
    * o nome do arquivo no formato ``AAAA-MM-DD_HHMM_<estado>.wav``.

    A primeira é preferível porque a rotulagem de anomalia depende de evidência
    externa (ordem de serviço, laudo) e não deve ficar codificada no nome.
    """
    gravacoes: list[dict] = []

    for pasta_unidade in sorted(p for p in entrada.iterdir() if p.is_dir()):
        unidade = pasta_unidade.name
        if unidade.startswith("."):
            continue

        planilha = pasta_unidade / "metadados.csv"
        if planilha.exists():
            with planilha.open(encoding="utf-8", newline="") as f:
                for linha in csv.DictReader(f):
                    caminho = pasta_unidade / linha["arquivo"]
                    if not caminho.exists():
                        log.warning("Arquivo listado em metadados.csv não encontrado: %s", caminho)
                        continue
                    referencia = linha.get("referencia") or ""
                    gravacoes.append(
                        {
                            "caminho": caminho,
                            "equipamento": linha.get("equipamento") or unidade,
                            "estado": (linha.get("estado") or "").strip().lower(),
                            "sessao_coleta": linha.get("sessao_coleta") or "",
                            "referencia": (pasta_unidade / referencia) if referencia else None,
                        }
                    )
            continue

        for caminho in sorted(pasta_unidade.glob("*.wav")):
            partes = caminho.stem.split("_")
            estado = partes[-1].lower() if partes else ""
            if estado not in ESTADOS_CONHECIDOS:
                log.warning(
                    "Estado não reconhecido em '%s' (esperado um de %s); "
                    "o segmento será rotulado como 'desconhecido'.",
                    caminho.name,
                    sorted(ESTADOS_CONHECIDOS),
                )
                estado = "desconhecido"
            gravacoes.append(
                {
                    "caminho": caminho,
                    "equipamento": unidade,
                    "estado": estado,
                    "sessao_coleta": "_".join(partes[:2]) if len(partes) >= 2 else "",
                    "referencia": _referencia_irma(caminho),
                }
            )

    return gravacoes


def _referencia_irma(caminho: Path) -> Path | None:
    """Procura a gravação de referência aplicável a uma gravação.

    A busca segue da correspondência mais forte para a mais fraca: mesma
    sessão, depois a referência mais próxima no tempo dentro da mesma unidade,
    depois um arquivo genérico. Exigir correspondência exata de sessão faria
    com que gravações feitas fora do horário da referência passassem **sem**
    subtração espectral, enquanto as demais passariam com ela — uma diferença
    de tratamento dentro do mesmo conjunto, que o classificador aprenderia como
    se fosse informação sobre o equipamento.
    """
    partes = caminho.stem.split("_")

    if len(partes) >= 2:
        candidata = caminho.with_name(f"{partes[0]}_{partes[1]}_referencia.wav")
        if candidata.exists():
            return candidata

    referencias = sorted(caminho.parent.glob("*_referencia.wav"))
    if referencias:
        # a mais próxima por ordem lexicográfica do prefixo de data e hora
        return min(referencias, key=lambda r: abs(_chave_temporal(r) - _chave_temporal(caminho)))

    candidata = caminho.parent / "referencia.wav"
    return candidata if candidata.exists() else None


def _chave_temporal(caminho: Path) -> int:
    """Extrai um inteiro comparável do prefixo ``AAAA-MM-DD_HHMM`` do nome."""
    partes = caminho.stem.split("_")
    digitos = "".join(c for c in "_".join(partes[:2]) if c.isdigit())
    return int(digitos) if digitos else 0


def processar_gravacao(
    gravacao: dict,
    saida: Path,
    p: ParametrosExtracao,
    *,
    rms_alvo: float,
    janela_s: float,
    sobreposicao: float,
    fator_subtracao: float,
    piso_espectral: float,
    banda_baseline: tuple[float, float],
    salvar_imagens: bool,
) -> list[dict]:
    """Processa uma gravação e devolve uma linha de metadados por segmento."""
    caminho = gravacao["caminho"]
    sinal, taxa = carregar_audio(caminho, taxa_alvo=p.taxa)

    referencia = None
    if gravacao.get("referencia") is not None and Path(gravacao["referencia"]).exists():
        referencia, _ = carregar_audio(gravacao["referencia"], taxa_alvo=p.taxa)
        referencia = normalizar_rms(referencia, alvo=rms_alvo)

    sinal = normalizar_rms(sinal, alvo=rms_alvo)
    sinal = aplicar_com_referencia(
        sinal,
        referencia,
        n_fft=p.n_fft,
        hop_length=p.hop_length,
        fator=fator_subtracao,
        piso=piso_espectral,
    )
    sinal = normalizar_rms(sinal, alvo=rms_alvo)

    segmentos = segmentar(sinal, taxa, janela_s=janela_s, sobreposicao=sobreposicao)
    if not segmentos:
        log.warning(
            "Gravação mais curta que a janela de %.1f s, ignorada: %s", janela_s, caminho.name
        )
        return []

    unidade = gravacao["equipamento"]
    base = saida / unidade / caminho.stem
    linhas: list[dict] = []

    for segmento in segmentos:
        prefixo = f"seg{segmento.indice:04d}"
        mfcc = mfcc_com_deltas(segmento.sinal, p)

        caminho_mfcc = base / "mfcc" / f"{prefixo}.npy"
        caminho_mfcc.parent.mkdir(parents=True, exist_ok=True)
        np.save(caminho_mfcc, mfcc)

        caminho_stft = caminho_mel = ""
        if salvar_imagens:
            caminho_stft = str(
                salvar_espectrograma(
                    espectrograma_stft_db(segmento.sinal, p),
                    base / "stft" / f"{prefixo}.png",
                    p=p,
                ).relative_to(saida)
            )
            caminho_mel = str(
                salvar_espectrograma(
                    espectrograma_mel_db(segmento.sinal, p),
                    base / "mel" / f"{prefixo}.png",
                    p=p,
                    eixo_mel=True,
                ).relative_to(saida)
            )

        linhas.append(
            {
                "arquivo_origem": str(caminho.relative_to(caminho.parents[1])),
                "indice_segmento": segmento.indice,
                "equipamento": unidade,
                "estado": gravacao["estado"],
                "sessao_coleta": gravacao.get("sessao_coleta", ""),
                "inicio_s": round(segmento.inicio_segundos(taxa), 3),
                "usou_referencia": int(referencia is not None),
                "energia_banda": energia_espectral_banda(
                    segmento.sinal, p, banda_hz=banda_baseline
                ),
                "caminho_stft": caminho_stft,
                "caminho_mel": caminho_mel,
                "caminho_mfcc": str(caminho_mfcc.relative_to(saida)),
            }
        )

    return linhas


def executar(
    entrada: Path,
    saida: Path,
    config: Config,
    *,
    salvar_imagens: bool | None = None,
) -> Path:
    """Executa a Camada 2 sobre todo o conjunto e grava os metadados."""
    p = ParametrosExtracao.da_config(config)
    rms_alvo = float(config.obter("preprocessamento.normalizacao_rms_alvo", 0.1))
    janela_s = float(config.obter("preprocessamento.segmentacao.janela_s", 2.0))
    sobreposicao = float(config.obter("preprocessamento.segmentacao.sobreposicao", 0.5))
    fator = float(config.obter("preprocessamento.subtracao_espectral.fator_super_subtracao", 1.0))
    piso = float(config.obter("preprocessamento.subtracao_espectral.piso_espectral", 0.02))
    banda = tuple(config.obter("modelos.baseline.banda_hz", [1000.0, 5000.0]))
    if salvar_imagens is None:
        salvar_imagens = bool(config.obter("caracteristicas.salvar_espectrogramas", True))

    if not entrada.exists():
        raise FileNotFoundError(
            f"Diretório de entrada não encontrado: {entrada}\n"
            "Baixe os dados do repositório indicado em data/README.md."
        )

    gravacoes = descobrir_gravacoes(entrada)
    if not gravacoes:
        raise RuntimeError(f"Nenhuma gravação encontrada em {entrada}")

    log.info("Encontradas %d gravações em %s", len(gravacoes), entrada)
    saida.mkdir(parents=True, exist_ok=True)

    todas_as_linhas: list[dict] = []
    for i, gravacao in enumerate(gravacoes, start=1):
        log.info("[%d/%d] %s", i, len(gravacoes), gravacao["caminho"].name)
        todas_as_linhas.extend(
            processar_gravacao(
                gravacao,
                saida,
                p,
                rms_alvo=rms_alvo,
                janela_s=janela_s,
                sobreposicao=sobreposicao,
                fator_subtracao=fator,
                piso_espectral=piso,
                banda_baseline=(float(banda[0]), float(banda[1])),
                salvar_imagens=salvar_imagens,
            )
        )

    destino = saida / "metadados_processados.csv"
    with destino.open("w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUNAS_METADADOS)
        escritor.writeheader()
        escritor.writerows(todas_as_linhas)

    log.info("%d segmentos gravados. Metadados em %s", len(todas_as_linhas), destino)
    return destino


def principal(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Camada 2 — pré-processamento e extração")
    parser.add_argument("--config", default=None, help="caminho do arquivo de configuração")
    parser.add_argument("--entrada", default=None, help="diretório com os dados brutos")
    parser.add_argument("--saida", default=None, help="diretório de saída dos artefatos")
    parser.add_argument(
        "--sem-imagens",
        action="store_true",
        help="não gerar os espectrogramas em PNG (execução mais rápida)",
    )
    parser.add_argument("--verboso", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verboso else logging.INFO,
        format="%(levelname)s  %(message)s",
    )

    config = Config.carregar(args.config)
    entrada = Path(args.entrada or RAIZ_PROJETO / "data" / "raw")
    saida = Path(args.saida or RAIZ_PROJETO / "data" / "processed")

    executar(
        entrada,
        saida,
        config,
        salvar_imagens=False if args.sem_imagens else None,
    )
    return 0


if __name__ == "__main__":
    sys.exit(principal())
