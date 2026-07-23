# Artefatos de integração (Camada 4)

Exportações **sanitizadas** do ambiente de monitoramento. Todo endereço,
credencial, comunidade SNMP e nome interno foi substituído por marcadores no
formato `<PREENCHER>`.

| Arquivo | O que é |
|---|---|
| `zabbix/template-snitch-inrow.sanitizado.yaml` | Template com os itens acústicos, gatilhos e severidades |
| `grafana/dashboard-linha-c.sanitizado.json` | Painel com estado, confiança e métricas SNMP correlacionadas |

## Importar no Zabbix

1. *Data collection → Templates → Import* e selecione o arquivo YAML.
2. Crie um host por evaporadora (`AC09` a `AC14`) e vincule o template.
3. Ajuste a macro `{$ACUSTICO.CONFIANCA.MIN}` ao patamar desejado.
4. Configure as ações de notificação com os destinatários da sua equipe.

Os itens são do tipo *trapper*: recebem valores enviados ativamente, sem
polling. O envio é feito por `zabbix_sender`, a partir de
`noisedc.integration.run`.

## Importar no Grafana

1. *Dashboards → New → Import* e cole o JSON.
2. Selecione a fonte de dados Zabbix quando solicitado.
3. Substitua os marcadores da variável `equipamento` pelos hosts reais.
4. Ajuste `<ITEM_TEMPERATURA_SNMP>` e `<ITEM_CARGA_SNMP>` aos nomes dos itens
   expostos pelas placas de gerência das suas unidades.

## Antes de commitar qualquer alteração

```bash
grep -rnE "([0-9]{1,3}\.){3}[0-9]{1,3}|\.ufrn\.br|community|password" deploy/
```

Se esse comando retornar algo além dos marcadores, o arquivo ainda não está
sanitizado. As exportações com valores reais ficam apenas no repositório de
dados privado (`08_INFRA_CONFIG/`).
