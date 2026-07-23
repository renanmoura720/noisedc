# Como contribuir

Este repositório acompanha uma dissertação de mestrado concluída. O código
está estável, mas issues e contribuições são bem-vindas — em especial:

- correções de bugs;
- extensão a outros modelos de evaporadora ou outros sensores;
- novos métodos de classificação, desde que sigam a interface de
  `noisedc.models.registry.criar_modelo`;
- melhorias de documentação.

## Antes de abrir um pull request

```bash
pip install -e ".[dev]"
ruff check src tests
pytest -q
bash scripts/verificar_dados_sensiveis.sh
```

Os três precisam passar. O terceiro existe porque este projeto lida com dados
de infraestrutura real: qualquer contribuição que inclua caminhos, endereços ou
credenciais de um ambiente específico será rejeitada, mesmo que
inadvertidamente.

## Estilo

- Nomes de função e variável em português, como o restante do código —
  mantenha a consistência com o que já existe;
- Docstrings explicando o *porquê* de uma decisão não óbvia, não apenas o
  *o quê* — funções triviais não precisam de docstring longa;
- Um teste para cada comportamento novo, em `tests/`, seguindo o padrão dos
  arquivos existentes (fixtures de áudio sintético em `tests/conftest.py`).

## Reportando problemas

Ao abrir uma issue, inclua a versão do Python, o comando executado e a saída
completa do erro. Se o problema envolver resultados divergentes dos
reportados na dissertação, veja antes
[`docs/reprodutibilidade.md`](docs/reprodutibilidade.md#divergências-esperadas).

## Código de conduta

Trate as demais pessoas com respeito. Discussões técnicas são bem-vindas;
ataques pessoais não.
