# Pendência de verificação — hiperparâmetros da Camada 3

**Status: aberta.** Não bloqueia o uso do repositório, mas precisa ser
resolvida antes de citar números específicos como definitivos.

## O que foi encontrado

Ao incorporar [`src/noisedc/legado/camada3_autoritativo_linha_c.py`](../src/noisedc/legado/camada3_autoritativo_linha_c.py)
— o script que efetivamente gerou as tabelas e figuras do Capítulo 5 —,
constatou-se que seus hiperparâmetros divergem dos reportados na Tabela 9 do
texto da dissertação:

| Hiperparâmetro | Tabela 9 (texto) | Script executado |
|---|---|---|
| SVM — `C` | 1,0 | 10 |
| Floresta Aleatória — nº de árvores | 100 | 400 |
| One-Class SVM — `ν` | 0,5 | 0,1 |

O baseline também difere em natureza, não só em parâmetro: a Tabela 9 descreve
um limiar sobre a energia espectral em uma banda diagnóstica fixa; o script
implementa, para cada dobra do `leave-one-unit-out`, a escolha da
característica de maior `|AUC − 0,5|` entre as 60 dimensões do descritor,
seguida do limiar de Youden sobre essa característica.

## Por que isso importa

Se os números publicados na dissertação correspondem à execução deste script,
a Tabela 9 precisa de errata. Se a Tabela 9 é que está correta, este script
não é a versão que gerou os resultados finais — e a versão que gerou precisa
ser localizada.

## Como resolver

1. Comparar as métricas impressas por este script (rode-o sobre
   `features_segmentos.csv` e confira os valores de recall, F1, AUC e taxa de
   falsos positivos) com as tabelas exatas do Capítulo 5 da dissertação
   depositada.
2. Se baterem → a dissertação precisa de uma errata nos valores da Tabela 9,
   ou uma nota explicando que a tabela descreve a *configuração de
   referência* testada, não a *configuração final* de produção.
3. Se não baterem → procurar no histórico do GitLab (`git log -p -- '**/*.py'`
   nos diretórios de Camada 3) por uma versão anterior do script mais próxima
   dos parâmetros da Tabela 9.

## Convenção adotada neste repositório enquanto a pendência está aberta

Os arquivos de configuração (`configs/config.example.yaml`,
`configs/params.yaml`) mantêm os valores da **Tabela 9** como padrão
documentado, por serem os publicamente citáveis no texto da dissertação. O
script em `src/noisedc/legado/` é preservado com os valores que ele de fato
usa, sem alteração — ele é evidência, não deve ser "corrigido" para bater com
a tabela.
