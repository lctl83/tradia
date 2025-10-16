# Documentation de l'API

## Endpoints disponibles

### 1. Page d'accueil

**GET /**

Affiche l'interface web de traduction.

**Réponse** : Page HTML

---

### 2. Health Check

**GET /healthz**

Vérifie la santé de l'application et la disponibilité d'Ollama.

**Réponse** :
```json
{
  "status": "healthy",
  "ollama_available": true,
  "ollama_url": "http://localhost:11434"
}
```

**Status** :
- `healthy` : Tout fonctionne
- `degraded` : Application OK mais Ollama indisponible

---

### 3. Métriques

**GET /metrics**

Retourne les statistiques d'utilisation de l'application.

**Réponse** :
```json
{
  "total_translations": 42,
  "total_segments_translated": 1250,
  "total_segments_failed": 3,
  "average_duration": 45.2
}
```

---

### 4. Traduire un fichier

**POST /translate**

Traduit un fichier XML SCENARI.

**Paramètres (multipart/form-data)** :

| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `file` | File | Oui | Fichier XML à traduire |
| `source_lang` | String | Oui | Langue source (`fr`, `en`, `ar`) |
| `target_lang` | String | Oui | Langue cible (`fr`, `en`, `ar`) |
| `model` | String | Non | Modèle Ollama (défaut: `llama3.2:latest`) |

**Contraintes** :
- Type MIME : `application/xml` ou `text/xml`
- Taille max : 50 MB (configurable)
- Source ≠ Cible

**Headers de réponse** :
- `Content-Type` : `application/xml`
- `Content-Disposition` : `attachment; filename="{nom}.{src}-{tgt}.{hash}.xml"`
- `X-Translation-Report` : JSON avec détails de traduction

**Réponse** : Fichier XML traduit

**Exemple avec curl** :

```bash
curl -X POST http://localhost:8000/translate \
  -F "file=@document.xml" \
  -F "source_lang=fr" \
  -F "target_lang=en" \
  -F "model=llama3.2:latest" \
  -o translated.xml \
  -D headers.txt
```

**Exemple avec Python** :

```python
import httpx

files = {'file': ('document.xml', open('document.xml', 'rb'), 'application/xml')}
data = {
    'source_lang': 'fr',
    'target_lang': 'en',
    'model': 'llama3.2:latest'
}

response = httpx.post(
    'http://localhost:8000/translate',
    files=files,
    data=data,
    timeout=300
)

if response.status_code == 200:
    # Récupérer le rapport
    report = response.headers.get('X-Translation-Report')
    
    # Sauvegarder le fichier traduit
    with open('translated.xml', 'wb') as f:
        f.write(response.content)
else:
    print(f"Error: {response.status_code}")
    print(response.json())
```

**Exemple avec JavaScript** :

```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('source_lang', 'fr');
formData.append('target_lang', 'en');
formData.append('model', 'llama3.2:latest');

const response = await fetch('http://localhost:8000/translate', {
    method: 'POST',
    body: formData
});

if (response.ok) {
    // Récupérer le rapport
    const report = JSON.parse(response.headers.get('X-Translation-Report'));
    console.log(report);
    
    // Télécharger le fichier
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'translated.xml';
    a.click();
}
```

---

## Structure du rapport de traduction

Le header `X-Translation-Report` contient un JSON avec :

```json
{
  "total_segments": 25,
  "translated": 23,
  "failed": 2,
  "ignored": 0,
  "duration_seconds": 45.3,
  "segments": [
    {
      "xpath": "/sc:item/sc:para[1]",
      "original": "Texte original...",
      "translated": "Translated text...",
      "success": true,
      "error": null
    },
    {
      "xpath": "/sc:item/sc:para[2]",
      "original": "Autre texte...",
      "translated": "",
      "success": false,
      "error": "Translation failed"
    }
  ]
}
```

---

## Codes d'erreur

| Code | Description |
|------|-------------|
| 200 | Succès |
| 400 | Requête invalide (mauvaises langues, XML invalide, etc.) |
| 413 | Fichier trop volumineux |
| 500 | Erreur serveur |

**Exemples d'erreurs 400** :

```json
{
  "detail": "Unsupported source language: de"
}
```

```json
{
  "detail": "Source and target languages must be different"
}
```

```json
{
  "detail": "Invalid XML file"
}
```

```json
{
  "detail": "No translatable segments found in XML"
}
```

---

## Langues supportées

| Code | Langue | Direction RTL |
|------|--------|---------------|
| `fr` | Français | Non |
| `en` | English | Non |
| `ar` | العربية | Oui |

---

## Modèles Ollama recommandés

| Modèle | Taille | Performance | Qualité |
|--------|--------|-------------|---------|
| `llama3.2:latest` | ~7B | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| `mistral:latest` | ~7B | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| `llama3:70b` | ~70B | ⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## Limitations

- **Taille de fichier** : 50 MB par défaut (configurable)
- **Timeout** : 120 secondes par segment (configurable)
- **Retries** : 3 tentatives par segment (configurable)
- **Formats** : Uniquement XML SCENARI
- **Persistance** : Aucune (traitement en mémoire)

---

## Exemples de scripts d'intégration

### Script Bash pour traiter plusieurs fichiers

```bash
#!/bin/bash

for file in *.xml; do
    echo "Traduction de $file..."
    curl -X POST http://localhost:8000/translate \
        -F "file=@$file" \
        -F "source_lang=fr" \
        -F "target_lang=en" \
        -o "translated_$file"
done
```

### Script Python pour traitement par lot

```python
import httpx
from pathlib import Path

def translate_file(file_path: Path, src: str, tgt: str):
    """Traduit un fichier."""
    with open(file_path, 'rb') as f:
        files = {'file': (file_path.name, f, 'application/xml')}
        data = {'source_lang': src, 'target_lang': tgt}
        
        response = httpx.post(
            'http://localhost:8000/translate',
            files=files,
            data=data,
            timeout=300
        )
        
        if response.status_code == 200:
            output = file_path.stem + f'.{src}-{tgt}.xml'
            with open(output, 'wb') as out:
                out.write(response.content)
            print(f"✓ {file_path.name} → {output}")
        else:
            print(f"✗ {file_path.name}: {response.status_code}")

# Traiter tous les fichiers XML
for xml_file in Path('.').glob('*.xml'):
    translate_file(xml_file, 'fr', 'en')
```

---

## Support et questions

Pour toute question sur l'API, consulter :
- Le code source dans `app/main.py`
- Les tests d'intégration dans `tests/test_integration.py`
- La documentation Swagger (bientôt disponible)
