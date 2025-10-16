#!/bin/bash

# Script pour développement local (sans Docker)
# Usage: ./dev.sh

set -e

echo "🔧 Mode développement - SCENARI Translator"
echo "=========================================="
echo

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé"
    exit 1
fi

echo "✓ Python $(python3 --version) détecté"

# Créer un environnement virtuel si nécessaire
if [ ! -d "venv" ]; then
    echo "📦 Création de l'environnement virtuel..."
    python3 -m venv venv
fi

# Activer l'environnement virtuel
echo "🔌 Activation de l'environnement virtuel..."
source venv/bin/activate

# Installer les dépendances
echo "📚 Installation des dépendances..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "✓ Dépendances installées"

# Vérifier Ollama
OLLAMA_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
echo
echo "🔍 Vérification d'Ollama à ${OLLAMA_URL}..."

if curl -s -f "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; then
    echo "✓ Ollama est accessible"
else
    echo "⚠️  Ollama n'est pas accessible - l'application pourrait ne pas fonctionner"
fi

# Démarrer l'application
echo
echo "🚀 Démarrage de l'application..."
echo "   URL : http://localhost:8000"
echo "   Press Ctrl+C to stop"
echo
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
