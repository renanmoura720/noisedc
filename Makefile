.PHONY: help setup preprocess train evaluate figures all seguranca limpar

help:
	@echo "setup       Instala dependências no ambiente virtual"
	@echo "preprocess  Camada 2 — pré-processamento e extração de características"
	@echo "train       Camada 3 — treinamento dos quatro métodos"
	@echo "evaluate    Camada 3 — avaliação LOUO e LORO"
	@echo "figures     Gera as figuras e tabelas"
	@echo "all         Pipeline completo"
	@echo "seguranca   Auditoria de dados sensíveis"

setup:
	python -m pip install -r requirements.txt

preprocess:
	python -m noisedc.preprocessing.run --config configs/config.yaml

train:
	python -m noisedc.models.train --config configs/config.yaml

evaluate:
	python -m noisedc.evaluation.run --protocol leave-one-unit-out
	python -m noisedc.evaluation.run --protocol leave-one-recording-out

figures:
	python -m noisedc.viz.build_figures

all: preprocess train evaluate figures

seguranca:
	bash scripts/verificar_dados_sensiveis.sh

limpar:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache
