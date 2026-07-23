"""Scripts autoritativos ou reconstruídos, preservados fora do padrão modular.

Diferente do restante de src/noisedc/, o conteúdo aqui não é refatorado nem
segue o guia de estilo do projeto. O valor deste diretório é ser a fonte da
verdade quando um número reportado precisa ser auditado.

Arquivos:

``camada3_autoritativo_linha_c.py``
    O script real, enviado pelo autor e preservado byte-a-byte. Executado
    sobre o features_segmentos.csv real, reproduz exatamente as Tabelas 12,
    13 e 14 do Capítulo 5 — ver docs/PENDENCIA-hiperparametros-camada3.md
    para a verificação completa.

``reconstrucao_camada2_extracao_features.py``
    RECONSTRUÇÃO (não o original). Produz um CSV no mesmo esquema de colunas
    do features_segmentos.csv real, a partir da convenção de nomes de
    arquivo observada nos dados (LINHAC-EVxx-AAAAMMDD-turno-codigo-NNN.wav) e
    do pipeline descrito no Capítulo 4. Testado de ponta a ponta e validado
    como compatível com camada3_autoritativo_linha_c.py.

``reconstrucao_camada4_integracao_zabbix.py``
    RECONSTRUÇÃO (não o original). Consolida predições por gravação (voto
    majoritário, mesma regra da Camada 3) e envia os itens trapper
    acustico.estado/acustico.confianca via zabbix_sender. Testado em modo de
    simulação.

Ciência aberta favorece preservar o artefato real, mesmo com suas
imperfeições, a reescrevê-lo silenciosamente para parecer mais organizado —
por isso o autoritativo nunca é "corrigido" para bater com convenções do
projeto, e as reconstruções são marcadas como tal em vez de apresentadas como
os originais.
"""
