#!/usr/bin/env python3
"""Script de monitoring pour SCENARI Translator."""

import sys
import json
import time
from datetime import datetime
try:
    import httpx
except ImportError:
    print("❌ httpx non installé. Installez avec: pip install httpx")
    sys.exit(1)


def check_endpoint(url: str, name: str) -> tuple[bool, str]:
    """Vérifie un endpoint."""
    try:
        response = httpx.get(url, timeout=5)
        if response.status_code == 200:
            return True, f"✓ {name} OK"
        else:
            return False, f"✗ {name} returned {response.status_code}"
    except Exception as e:
        return False, f"✗ {name} error: {str(e)}"


def main():
    """Fonction principale."""
    print("=" * 60)
    print("   SCENARI Translator - Health Check")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    base_url = "http://localhost:8000"
    all_ok = True

    # Vérifier les endpoints
    endpoints = [
        (f"{base_url}/", "Home Page"),
        (f"{base_url}/healthz", "Health Check"),
        (f"{base_url}/metrics", "Metrics"),
    ]

    for url, name in endpoints:
        ok, msg = check_endpoint(url, name)
        print(msg)
        if not ok:
            all_ok = False

    print()

    # Vérifier Ollama
    print("Checking Ollama...")
    ollama_url = "http://localhost:11434/api/tags"
    ok, msg = check_endpoint(ollama_url, "Ollama")
    print(msg)
    if not ok:
        all_ok = False

    print()
    print("=" * 60)

    # Détails du healthcheck
    try:
        response = httpx.get(f"{base_url}/healthz", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("Health Details:")
            print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Could not get health details: {e}")

    print()

    # Métriques
    try:
        response = httpx.get(f"{base_url}/metrics", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("Metrics:")
            print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Could not get metrics: {e}")

    print()
    print("=" * 60)

    if all_ok:
        print("✓ All systems operational")
        return 0
    else:
        print("✗ Some systems are down")
        return 1


if __name__ == "__main__":
    sys.exit(main())
