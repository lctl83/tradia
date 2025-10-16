.PHONY: help build up down restart logs test clean install dev

# Variables - Détection automatique de Docker Compose v1 ou v2
DOCKER_COMPOSE := $(shell docker compose version > /dev/null 2>&1 && echo 'docker compose' || echo 'docker-compose')
DOCKER_EXEC = $(DOCKER_COMPOSE) exec scenari-translator

help: ## Afficher cette aide
	@echo "SCENARI Translator - Commandes disponibles :"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Construire l'image Docker
	$(DOCKER_COMPOSE) build

up: ## Démarrer l'application
	$(DOCKER_COMPOSE) up -d
	@echo "Application démarrée sur http://localhost:8000"

down: ## Arrêter l'application
	$(DOCKER_COMPOSE) down

restart: ## Redémarrer l'application
	$(DOCKER_COMPOSE) restart

logs: ## Afficher les logs
	$(DOCKER_COMPOSE) logs -f

ps: ## Afficher l'état des conteneurs
	$(DOCKER_COMPOSE) ps

health: ## Vérifier la santé de l'application
	@curl -s http://localhost:8000/healthz | python -m json.tool

metrics: ## Afficher les métriques
	@curl -s http://localhost:8000/metrics | python -m json.tool

test: ## Lancer les tests
	$(DOCKER_EXEC) pytest -v

test-cov: ## Lancer les tests avec coverage
	$(DOCKER_EXEC) pytest --cov=app --cov-report=html --cov-report=term

test-unit: ## Lancer uniquement les tests unitaires
	$(DOCKER_EXEC) pytest tests/test_xml_processor.py tests/test_translator.py -v

test-integration: ## Lancer uniquement les tests d'intégration
	$(DOCKER_EXEC) pytest tests/test_integration.py -v

shell: ## Ouvrir un shell dans le conteneur
	$(DOCKER_EXEC) /bin/bash

clean: ## Nettoyer les fichiers temporaires et les conteneurs
	$(DOCKER_COMPOSE) down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .pytest_cache/ .coverage

install: ## Installer les dépendances localement (développement)
	pip install -r requirements.txt

dev: ## Démarrer en mode développement (hot reload)
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

format: ## Formater le code avec black
	$(DOCKER_EXEC) black app/ tests/

lint: ## Vérifier le code avec flake8
	$(DOCKER_EXEC) flake8 app/ tests/

type-check: ## Vérifier les types avec mypy
	$(DOCKER_EXEC) mypy app/

rebuild: down build up ## Reconstruire et redémarrer

deploy: build up health ## Déployer l'application et vérifier la santé

status: ## Afficher le status complet
	@echo "=== Status des conteneurs ==="
	@$(DOCKER_COMPOSE) ps
	@echo ""
	@echo "=== Healthcheck ==="
	@curl -s http://localhost:8000/healthz | python -m json.tool || echo "Application non accessible"
	@echo ""
	@echo "=== Métriques ==="
	@curl -s http://localhost:8000/metrics | python -m json.tool || echo "Métriques non disponibles"

backup-logs: ## Sauvegarder les logs
	@mkdir -p backups
	$(DOCKER_COMPOSE) logs > backups/logs-$$(date +%Y%m%d-%H%M%S).txt
	@echo "Logs sauvegardés dans backups/"

update: ## Mettre à jour et redéployer
	git pull
	$(MAKE) rebuild

# Valeur par défaut
.DEFAULT_GOAL := help
