"""Carregamento de configuração do projeto.

Separa deliberadamente dois tipos de parâmetro:

* **parâmetros científicos** (taxa de amostragem, janela, número de MFCC,
  hiperparâmetros dos modelos) ficam em ``configs/config.yaml``, versionado e
  público, porque são necessários para reproduzir os resultados;
* **parâmetros de ambiente** (endereços de servidor, tokens, credenciais) vêm
  de variáveis de ambiente ou do arquivo ``.env``, que nunca é versionado.

Essa separação é o que permite publicar a configuração completa do experimento
sem expor a infraestrutura em que ele foi executado.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
CONFIG_PADRAO = RAIZ_PROJETO / "configs" / "config.yaml"
CONFIG_EXEMPLO = RAIZ_PROJETO / "configs" / "config.example.yaml"


class ErroDeConfiguracao(RuntimeError):
    """Configuração ausente, malformada ou incompleta."""


def _carregar_dotenv(caminho: Path) -> None:
    """Carrega ``.env`` sem depender de biblioteca externa.

    Variáveis já presentes no ambiente têm precedência, de modo que a execução
    em CI ou em contêiner possa sobrescrever o arquivo local.
    """
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        os.environ.setdefault(chave.strip(), valor.strip().strip("\"'"))


@dataclass
class Config:
    """Configuração do projeto, com acesso por caminho pontilhado."""

    dados: dict[str, Any] = field(default_factory=dict)
    caminho: Path | None = None

    @classmethod
    def carregar(cls, caminho: str | Path | None = None) -> Config:
        caminho = Path(caminho) if caminho else CONFIG_PADRAO
        if not caminho.exists():
            if CONFIG_EXEMPLO.exists():
                try:
                    dica = (
                        f"Copie o modelo com:  cp {CONFIG_EXEMPLO.relative_to(RAIZ_PROJETO)} "
                        f"{caminho.relative_to(RAIZ_PROJETO)}"
                    )
                except ValueError:
                    # 'caminho' está fora da árvore do projeto (comum em testes,
                    # que usam diretórios temporários); a dica relativa não se
                    # aplica, mas o erro ainda deve ser informativo.
                    dica = f"Copie o modelo de configuração para: {caminho}"
                raise ErroDeConfiguracao(
                    f"Arquivo de configuração não encontrado: {caminho}\n{dica}"
                )
            raise ErroDeConfiguracao(f"Arquivo de configuração não encontrado: {caminho}")

        _carregar_dotenv(RAIZ_PROJETO / ".env")
        with caminho.open(encoding="utf-8") as f:
            dados = yaml.safe_load(f) or {}
        return cls(dados=dados, caminho=caminho)

    def obter(self, chave: str, padrao: Any = None) -> Any:
        """Acessa um valor por caminho pontilhado: ``obter('caracteristicas.n_mfcc')``."""
        no: Any = self.dados
        for parte in chave.split("."):
            if not isinstance(no, dict) or parte not in no:
                return padrao
            no = no[parte]
        return no

    def exigir(self, chave: str) -> Any:
        valor = self.obter(chave)
        if valor is None:
            raise ErroDeConfiguracao(
                f"Parâmetro obrigatório ausente na configuração: '{chave}'"
            )
        return valor

    def __getitem__(self, chave: str) -> Any:
        return self.exigir(chave)


def variavel_de_ambiente(nome: str, padrao: str | None = None, *, obrigatoria: bool = False) -> str | None:
    """Lê uma variável de ambiente, com mensagem de erro útil quando ausente."""
    _carregar_dotenv(RAIZ_PROJETO / ".env")
    valor = os.environ.get(nome, padrao)
    if obrigatoria and not valor:
        raise ErroDeConfiguracao(
            f"Variável de ambiente '{nome}' não definida. "
            "Copie .env.example para .env e preencha os valores do seu ambiente."
        )
    return valor
