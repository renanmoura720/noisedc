"""Camada 4 — integração com o Zabbix.

Converte o resultado da Camada 3 em evento operacional rastreável. Cada
equipamento é um host, sob o qual dois itens do tipo *trapper* recebem os
valores enviados pelo pipeline:

===========================  ==========  ==========================================
Item                         Tipo        Conteúdo
===========================  ==========  ==========================================
``acustico.estado``          inteiro     0 = normal, 1 = anômalo
``acustico.confianca``       flutuante   grau de confiança da classificação
===========================  ==========  ==========================================

O contrato de interface é deliberadamente estreito: a Camada 4 depende apenas
do **formato do registro recebido**, não do método que o produziu. Trocar o
classificador da Camada 3 não exige alterar nada aqui.

Nenhum endereço, credencial ou nome de host é embutido neste módulo: tudo vem
de variáveis de ambiente definidas em ``.env``, que não é versionado.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from noisedc.config import variavel_de_ambiente

log = logging.getLogger(__name__)

ITEM_ESTADO_PADRAO = "acustico.estado"
ITEM_CONFIANCA_PADRAO = "acustico.confianca"

# Severidades do Zabbix: 0 não classificado, 1 informativo, 2 aviso,
# 3 médio, 4 alto, 5 desastre.
SEVERIDADES = {
    "informativo": 1,
    "aviso": 2,
    "medio": 3,
    "alto": 4,
}


@dataclass
class Evento:
    """Um evento operacional, com o mínimo necessário para ser rastreável.

    Reúne origem, significado e caminho de volta ao dado bruto: sem o
    identificador do áudio, um alerta não pode ser auditado depois.
    """

    equipamento: str
    estado: int
    confianca: float
    arquivo_audio: str = ""
    dispositivo: str = ""
    momento: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def anomalo(self) -> bool:
        return self.estado == 1

    def severidade(self, *, confianca_minima: float = 0.80) -> str:
        """Classifica a severidade a partir do estado e do grau de confiança.

        A escala ordena a resposta das equipes pela criticidade e evita que
        uma variação acústica leve receba o mesmo tratamento que um padrão
        incompatível com a operação normal.
        """
        if not self.anomalo:
            return "informativo"
        if self.confianca < confianca_minima:
            return "aviso"
        if self.confianca < 0.95:
            return "medio"
        return "alto"

    def como_dicionario(self) -> dict:
        return {
            "equipamento": self.equipamento,
            "estado": self.estado,
            "confianca": round(float(self.confianca), 4),
            "severidade": self.severidade(),
            "arquivo_audio": self.arquivo_audio,
            "dispositivo": self.dispositivo,
            "momento": self.momento.isoformat(timespec="seconds"),
        }


class ClienteZabbix:
    """Envia valores ao Zabbix pelo utilitário ``zabbix_sender``.

    Opera em modo de simulação por padrão: sem ``--enviar`` explícito, os
    comandos são registrados mas não executados. Isso permite validar a cadeia
    completa — classificação, formatação do registro, mapeamento de severidade
    — sem depender de acesso à rede de gerência.
    """

    def __init__(
        self,
        servidor: str | None = None,
        porta: int | None = None,
        *,
        simular: bool = True,
        caminho_sender: str | None = None,
    ):
        self.servidor = servidor or variavel_de_ambiente("ZABBIX_SERVER")
        self.porta = int(porta or variavel_de_ambiente("ZABBIX_PORTA", "10051"))
        self.simular = simular
        self.caminho_sender = caminho_sender or shutil.which("zabbix_sender")

        if not self.simular:
            if not self.servidor:
                raise RuntimeError(
                    "ZABBIX_SERVER não definido. Copie .env.example para .env e preencha-o, "
                    "ou execute em modo de simulação."
                )
            if not self.caminho_sender:
                raise RuntimeError(
                    "Utilitário 'zabbix_sender' não encontrado no PATH. "
                    "Instale o pacote zabbix-sender da sua distribuição."
                )

    def enviar_evento(self, evento: Evento, *, item_estado: str = ITEM_ESTADO_PADRAO,
                      item_confianca: str = ITEM_CONFIANCA_PADRAO) -> list[str]:
        """Envia estado e confiança de um evento. Retorna os comandos executados."""
        comandos = [
            self._montar_comando(evento.equipamento, item_estado, str(evento.estado)),
            self._montar_comando(
                evento.equipamento, item_confianca, f"{evento.confianca:.4f}"
            ),
        ]

        for comando in comandos:
            if self.simular:
                log.info("[simulação] %s", " ".join(comando))
                continue
            resultado = subprocess.run(comando, capture_output=True, text=True, timeout=30)
            if resultado.returncode != 0:
                log.error(
                    "Falha no envio ao Zabbix (host %s): %s",
                    evento.equipamento,
                    resultado.stderr.strip() or resultado.stdout.strip(),
                )
            else:
                log.debug("Envio concluído: %s", resultado.stdout.strip())

        return [" ".join(c) for c in comandos]

    def _montar_comando(self, host: str, chave: str, valor: str) -> list[str]:
        return [
            self.caminho_sender or "zabbix_sender",
            "-z", self.servidor or "<ZABBIX_SERVER>",
            "-p", str(self.porta),
            "-s", host,
            "-k", chave,
            "-o", valor,
        ]


def escrever_lote(eventos: list[Evento], destino: str | Path) -> Path:
    """Grava os eventos no formato de arquivo do ``zabbix_sender`` (``-i``).

    Cada linha segue ``<host> <chave> <valor>``. Útil para envio em lote ao
    final do processamento de um conjunto de gravações e para inspeção do que
    seria enviado antes de enviá-lo de fato.
    """
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)

    linhas: list[str] = []
    for evento in eventos:
        linhas.append(f"{evento.equipamento} {ITEM_ESTADO_PADRAO} {evento.estado}")
        linhas.append(f"{evento.equipamento} {ITEM_CONFIANCA_PADRAO} {evento.confianca:.4f}")

    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return destino
