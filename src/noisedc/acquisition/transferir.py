"""Camada 1 — transferência das gravações e registro dos metadados de coleta.

Roda no servidor, não no dispositivo. Recupera os arquivos gravados pelo
protótipo, organiza-os na estrutura esperada pela Camada 2 e registra os
metadados de coleta.

Todos os parâmetros de conexão vêm de variáveis de ambiente. Nenhum endereço,
usuário ou chave é embutido no código: o mesmo script funciona em qualquer
instalação, e o repositório não revela nada sobre a rede em que os
experimentos foram conduzidos.

Uso::

    python -m noisedc.acquisition.transferir --equipamento EV11 --estado normal
    python -m noisedc.acquisition.transferir --equipamento EV11 --origem-local /media/pendrive
"""

from __future__ import annotations

import argparse
import csv
import logging
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from noisedc.config import RAIZ_PROJETO, variavel_de_ambiente

log = logging.getLogger(__name__)

ESTADOS = ("normal", "anomalia", "standby", "referencia")


def transferir_por_ssh(destino: Path, *, origem_remota: str = "/mnt/sda1/gravacoes") -> list[Path]:
    """Copia as gravações do dispositivo por SSH.

    Requer ``DISPOSITIVO_HOST`` e ``DISPOSITIVO_USUARIO`` no ambiente. A chave
    privada, quando usada, é referenciada por caminho em
    ``DISPOSITIVO_CHAVE_SSH`` — nunca embutida.
    """
    host = variavel_de_ambiente("DISPOSITIVO_HOST", obrigatoria=True)
    usuario = variavel_de_ambiente("DISPOSITIVO_USUARIO", "root")
    chave = variavel_de_ambiente("DISPOSITIVO_CHAVE_SSH")

    if not shutil.which("scp"):
        raise RuntimeError("Utilitário 'scp' não encontrado no PATH.")

    destino.mkdir(parents=True, exist_ok=True)
    comando = ["scp", "-r"]
    if chave:
        comando += ["-i", chave]
    comando += [f"{usuario}@{host}:{origem_remota}/*.wav", str(destino)]

    log.info("Transferindo de %s@%s:%s", usuario, host, origem_remota)
    resultado = subprocess.run(comando, capture_output=True, text=True, timeout=600)
    if resultado.returncode != 0:
        raise RuntimeError(f"Falha na transferência: {resultado.stderr.strip()}")

    return sorted(destino.glob("*.wav"))


def copiar_de_pasta(origem: Path, destino: Path) -> list[Path]:
    """Copia as gravações de uma pasta local (cartão SD, pendrive, montagem)."""
    if not origem.exists():
        raise FileNotFoundError(f"Origem não encontrada: {origem}")

    destino.mkdir(parents=True, exist_ok=True)
    copiados: list[Path] = []
    for arquivo in sorted(origem.glob("*.wav")):
        alvo = destino / arquivo.name
        shutil.copy2(arquivo, alvo)
        copiados.append(alvo)

    return copiados


def registrar_metadados(
    pasta_unidade: Path,
    arquivos: list[Path],
    *,
    equipamento: str,
    estado: str,
    sessao: str,
    referencia: str = "",
    observacoes: str = "",
) -> Path:
    """Acrescenta as gravações ao ``metadados.csv`` da unidade.

    O rótulo de estado é registrado aqui, no momento da coleta, e não inferido
    depois a partir do sinal — a rotulagem de anomalia depende de evidência
    externa (ordem de serviço, laudo, observação da equipe), e derivá-la do
    próprio áudio tornaria a avaliação circular.
    """
    if estado not in ESTADOS:
        raise ValueError(f"Estado inválido: '{estado}'. Use um de {ESTADOS}.")

    planilha = pasta_unidade / "metadados.csv"
    colunas = [
        "arquivo", "equipamento", "estado", "sessao_coleta",
        "referencia", "coletado_em", "observacoes",
    ]

    existentes: set[str] = set()
    if planilha.exists():
        with planilha.open(encoding="utf-8", newline="") as f:
            existentes = {linha["arquivo"] for linha in csv.DictReader(f)}

    novo = not planilha.exists()
    with planilha.open("a", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=colunas)
        if novo:
            escritor.writeheader()
        for arquivo in arquivos:
            if arquivo.name in existentes:
                log.debug("Já registrado, ignorando: %s", arquivo.name)
                continue
            escritor.writerow(
                {
                    "arquivo": arquivo.name,
                    "equipamento": equipamento,
                    "estado": estado,
                    "sessao_coleta": sessao,
                    "referencia": referencia,
                    "coletado_em": datetime.now().isoformat(timespec="seconds"),
                    "observacoes": observacoes,
                }
            )

    return planilha


def principal(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Camada 1 — transferência e registro")
    parser.add_argument("--equipamento", required=True, help="identificador da unidade (ex.: EV11)")
    parser.add_argument("--estado", required=True, choices=ESTADOS)
    parser.add_argument("--sessao", default=None, help="identificador da sessão de coleta")
    parser.add_argument("--referencia", default="", help="arquivo de referência da sessão")
    parser.add_argument("--observacoes", default="")
    parser.add_argument("--origem-local", default=None, help="copiar de uma pasta em vez de SSH")
    parser.add_argument("--destino", default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    raiz = Path(args.destino or RAIZ_PROJETO / "data" / "raw")
    pasta_unidade = raiz / args.equipamento
    sessao = args.sessao or datetime.now().strftime("%Y-%m-%d_%H%M")

    if args.origem_local:
        arquivos = copiar_de_pasta(Path(args.origem_local), pasta_unidade)
    else:
        arquivos = transferir_por_ssh(pasta_unidade)

    if not arquivos:
        log.warning("Nenhuma gravação transferida.")
        return 1

    planilha = registrar_metadados(
        pasta_unidade,
        arquivos,
        equipamento=args.equipamento,
        estado=args.estado,
        sessao=sessao,
        referencia=args.referencia,
        observacoes=args.observacoes,
    )

    log.info("%d gravações em %s", len(arquivos), pasta_unidade)
    log.info("Metadados atualizados em %s", planilha)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
