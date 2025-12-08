# Documentation de l'API IA DCI

## Endpoints disponibles

### 1. Page d'accueil

**GET /**

Affiche l'interface web des assistants IA DCI.

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
  "text_translations": 12,
  "corrections": 5,
  "reformulations": 3,
  "meeting_summaries": 2
}
```

---

### 4. Liste des modèles

**GET /models**

Retourne la liste des modèles Ollama disponibles côté serveur. Le modèle par défaut (`mistral-small3.2:latest`) est toujours positionné en tête de liste.

**Réponse** :
```json
{
  "models": ["mistral-small3.2:latest", "model-b"],
  "default_model": "mistral-small3.2:latest"
}
```

---

### 5. Traduction de texte

**POST /translate-text**

Traduit un texte brut entre les langues supportées (FR/EN/AR).

**Paramètres (form-data)** :

| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `text` | String | Oui | Texte à traduire |
| `source_lang` | String | Oui | Langue source (`fr`, `en`, `ar`) |
| `target_lang` | String | Oui | Langue cible (`fr`, `en`, `ar`) |
| `model` | String | Non | Modèle Ollama (défaut : `mistral-small3.2:latest`) |

**Réponse** :

```json
{
  "translated_text": "Translation result"
}
```

**Codes d'erreur courants** :
- `400` : Langue non supportée, texte vide ou source = cible
- `502` : Erreur de génération côté Ollama

---

### 6. Correction orthographique

**POST /correct-text**

Retourne le texte corrigé accompagné d'explications sur les modifications.

**Paramètres (form-data)** :

| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `text` | String | Oui | Texte à corriger |
| `model` | String | Non | Modèle Ollama |

**Réponse** :

```json
{
  "corrected_text": "Texte corrigé",
  "explanations": ["Accord sujet/verbe", "Ponctuation ajustée"]
}
```

**Codes d'erreur courants** :
- `400` : Texte vide
- `502` : Réponse non exploitable du modèle

---

### 7. Reformulation

**POST /reformulate-text**

Reformule un texte tout en conservant le sens et met en avant les principales améliorations.

**Paramètres (form-data)** :

| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `text` | String | Oui | Texte à reformuler |
| `model` | String | Non | Modèle Ollama |

**Réponse** :

```json
{
  "reformulated_text": "Version reformulée",
  "highlights": ["Tonalité plus professionnelle", "Clarification du message"]
}
```

---

### 8. Compte rendu de réunion

**POST /meeting-summary**

Génère un résumé structuré à partir de notes de réunion.

**Paramètres (form-data)** :

| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `text` | String | Oui | Notes de réunion |
| `model` | String | Non | Modèle Ollama |

**Réponse** :

```json
{
  "summary": "Résumé synthétique",
  "decisions": ["Décision 1"],
  "action_items": ["Action 1"]
}
```

---

Chaque endpoint renvoie des erreurs détaillées au format JSON (`{"detail": "message"}`) afin de faciliter l'intégration côté client.
