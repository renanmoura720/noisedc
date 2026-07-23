# Notebooks

Espaço para exploração e análises pontuais. Os resultados que sustentam a
dissertação são gerados pelos scripts em `src/noisedc/`, não pelos notebooks —
um notebook pode inspecionar ou visualizar um resultado já calculado, mas não é
a fonte dele.

## Antes de commitar

```bash
jupyter nbconvert --clear-output --inplace notebooks/*.ipynb
```

Ou instale o hook automático:

```bash
pip install nbstripout && nbstripout --install
```

Saídas de notebook costumam conter caminhos absolutos, nomes de host e
amostras de dados que não aparecem no código-fonte, e por isso merecem atenção
extra na auditoria de sanitização.
