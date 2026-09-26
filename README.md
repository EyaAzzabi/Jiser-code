# JISER (جسر) · Le pont entre le contribuable et l'administration fiscale

Prototype pour le Hackathon national « IA & Finances publiques » (25–26 septembre 2026).

JISER est une plateforme d'IA pour le **contentieux fiscal tunisien**. Elle a trois espaces :

- **Entreprise et conseil** : l'utilisateur dépose sa notification de redressement. JISER l'explique chef par chef, contrôle la procédure (CDPF), estime ce qui est contestable, cite les articles de loi, calcule la date limite et rédige un brouillon de réponse.
- **Administration** : contrôle qualité d'une notification avant envoi, stock de dossiers trié par montant recouvrable, score de solidité expliqué (SHAP), proposition de conciliation, tableau de bord.
- **Admin plateforme** : utilisateurs et rôles, base juridique, journal de chaque recommandation de l'IA.

Chaque explication peut être **écoutée à voix haute en français, en anglais ou en tounsi** (synthèse vocale OpenAI).

L'accès passe par un **onboarding sécurisé par code OTP**, avec des étapes propres à chaque profil (entreprise, conseil, vérificateur, chef du contentieux, administrateur).

Défis traités : **T3** (principal), T9, T14, T20.

## Lancer le projet

Prérequis : Python 3.11+, Node 20+.

```bash
# 1. Backend
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.txt     # Windows
cp .env.example .env            # puis remplir les clés (voir ci-dessous)
.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --port 8000

# 2. Frontend (autre terminal)
cd frontend && npm install && npm run dev      # http://localhost:5173
```

Documentation de l'API (Swagger) : http://localhost:8000/docs

### Configuration (`.env`)

| Service | Rôle | Mise en place |
|---|---|---|
| **OpenAI** | IA principale : lecture des photos, explications en français et en tounsi, assistant, rédaction, avis juridique | `OPENAI_API_KEY` (modèle par défaut `gpt-5.4-mini`, réglable par `OPENAI_MODEL`) |
| **Gemini** (gratuit) | IA de secours automatique si OpenAI ne répond pas | Clé sur https://aistudio.google.com/apikey → `GEMINI_API_KEY` |
| **Supabase** | Base de données : comptes, sessions, codes OTP (hachés), analyses, réponses, journal, dossiers | Créer un projet → SQL Editor → exécuter `supabase/schema.sql` → `SUPABASE_URL` et `SUPABASE_SERVICE_KEY` (Project Settings › API) → `python scripts/seed_supabase.py` |
| **n8n** | E-mails : code OTP, bienvenue à l'activation du compte, échéance enregistrée puis rappels à J-15, J-7, J-3 et J-1 (envoyés par l'API toutes les 6 heures) | Importer les fichiers de `n8n/` (OTP, bienvenue, rappel poussé par l'API), choisir un identifiant SMTP (ex. Gmail + mot de passe d'application), remplacer `CHANGE_ME_SECRET` par `N8N_SHARED_SECRET`, activer, puis copier les URL de production des webhooks dans `N8N_OTP_WEBHOOK_URL` et `N8N_WELCOME_WEBHOOK_URL` |
| **Admin plateforme** | Espace privé `/plateforme` | Mettre les e-mails autorisés dans `ADMIN_EMAILS` |

Sans ces services, l'application reste utilisable : IA remplacée par les règles et le modèle ML, base en mémoire, et codes OTP écrits uniquement dans le journal du serveur (jamais affichés à l'écran).

### Sécurité

- Accès par **code à usage unique envoyé par e-mail** : 6 chiffres, 5 minutes, 5 essais, usage unique, renvoi limité à un code toutes les 30 secondes ; seul un hachage salé est stocké.
- Jeton de session aléatoire (256 bits), stocké haché, valable 8 heures.
- Contrôle d'accès par rôle sur chaque route de l'API (entreprise / administration / administrateur).
- L'espace administrateur n'apparaît nulle part dans l'interface : accessible uniquement par son lien et pour les e-mails autorisés.
- Supabase : Row Level Security activée sans politique publique ; seule l'API (clé service) accède aux données.
- Chaque recommandation de l'IA et chaque décision humaine est inscrite au journal.

## Reproduire les données et le modèle

```bash
.venv/Scripts/python scripts/scrape_legal.py        # textes de loi -> data/legal/
.venv/Scripts/python scripts/generate_synthetic.py  # dossiers synthétiques + PDF de démo
.venv/Scripts/python scripts/train_model.py         # modèle XGBoost + models/metrics.json
```

## Architecture

```
frontend/ (React + TypeScript + Vite + Tailwind + Recharts)
   │  /api (proxy Vite)
backend/app (FastAPI)
   ├─ services/extraction.py   PDF / photo / texte -> notification structurée (parseur + Claude)
   ├─ services/procedure.py    règles de procédure du CDPF (art. 19, 39, 40, 43, 44)
   ├─ services/legal_rag.py    recherche BM25 dans 274 articles (CDPF, TVA, IRPP/IS)
   ├─ services/scoring.py      XGBoost 3 classes par chef + explications SHAP
   ├─ services/analysis.py     analyse côté contribuable
   ├─ services/drafting.py     brouillon de réponse (art. 44)
   ├─ services/administration.py  tri, conciliation, tableau de bord
   ├─ services/auth.py         OTP (haché, 5 min, 5 essais, anti-rejeu) et sessions
   └─ services/llm.py          Claude (sorties structurées, cache, mode hors ligne)
scripts/  scraping, génération de données, entraînement
data/     textes de loi, dossiers synthétiques, PDF de démo
models/   modèle entraîné et métriques
```

## Résultats mesurés (données synthétiques)

Voir `models/metrics.json`. Sur 625 dossiers de test : AUC 0,71 par chef ; avec une capacité de traitement de 20 % des dossiers, le tri JISER recouvre environ 3,7 fois plus (+269 %) que le traitement par ancienneté. Ces chiffres sont mesurés sur des données simulées : le modèle doit être réentraîné sur l'historique réel de l'administration.

## Sources, modèles et bibliothèques

- Textes de loi : [Jurisite Tunisie](https://www.jurisitetunisie.com) (CDPF, Code de la TVA, Code de l'IRPP et de l'IS), version publiée sur le site ; à vérifier avec les dernières lois de finances.
- LLM : OpenAI (gpt-5.4-mini) en principal, Gemini (Google AI Studio, niveau gratuit) en secours automatique ; Claude (Anthropic) en option.
- Automatisation : n8n (e-mails). Base de données : Supabase (PostgreSQL).
- Bibliothèques : FastAPI, Pydantic, XGBoost, SHAP, scikit-learn, rank-bm25, pypdf, ReportLab, React, Tailwind CSS, Recharts, lucide-react.
- Données : entièrement synthétiques (aucune donnée réelle de contribuable).

## Limites

- Modèle entraîné sur données synthétiques (règles métier + bruit).
- Les comptes de l'administration (vérificateurs, contentieux) devraient être validés par un administrateur avant activation.
- L'IA recommande et explique ; la décision reste humaine.
