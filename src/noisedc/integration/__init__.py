"""Camada 4 — integração com sistemas de monitoramento e alerta."""

from noisedc.integration.zabbix import ClienteZabbix, Evento, escrever_lote

__all__ = ["ClienteZabbix", "Evento", "escrever_lote"]
