"""NoiseDC — monitoramento acústico e detecção de anomalias em data centers.

Arquitetura modular de quatro camadas:

1. ``acquisition``     — aquisição por dispositivo IoT de baixo custo
2. ``preprocessing`` + ``features`` — condicionamento e representações
3. ``models`` + ``evaluation``      — classificação e validação
4. ``integration``                  — Zabbix, Grafana e alertas

Referência: SILVA, R. M. Arquitetura para monitoramento e detecção de anomalias
acústicas em data centers. Dissertação (Mestrado em Tecnologia da Informação) —
IMD/UFRN, Natal, 2026.
"""

__version__ = "1.0.0"
__all__ = ["config", "dataset"]
