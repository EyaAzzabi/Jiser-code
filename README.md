# JISER (جسر) · Le pont entre le contribuable et l'administration fiscale

Prototype pour le Hackathon national « IA & Finances publiques » (25–26 septembre 2026).

JISER est une plateforme d'IA pour le **contentieux fiscal tunisien**. Elle a trois espaces :

- **Entreprise et conseil** : l'utilisateur dépose sa notification de redressement. JISER l'explique chef par chef, contrôle la procédure (CDPF), estime ce qui est contestable, cite les articles de loi, calcule la date limite et rédige un brouillon de réponse.
- **Administration** : contrôle qualité d'une notification avant envoi, stock de dossiers trié par montant recouvrable, score de solidité expliqué (SHAP), proposition de conciliation, tableau de bord.
- **Admin plateforme** : utilisateurs et rôles, base juridique, journal de chaque recommandation de l'IA.

L'accès passe par un **onboarding sécurisé par code OTP**, avec des étapes propres à chaque profil (entreprise, conseil, vérificateur, chef du contentieux, administrateur).

Défis traités : **T3** (principal), T9, T14, T20.

## Lancer le projet

Prérequis : Python 3.11+, Node 20+.

```bash
# 1. Backend
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.txt     # Windows
# source .venv/bin/activate && pip install -r backend/requirements.txt   # macOS / Linux
cp .env.example .env            # ajouter ANTHROPIC_API_KEY (facultatif)
.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --port 8000

# 2. Frontend (autre terminal)
cd frontend
npm install
npm run dev                      # http://localhost:5173
```

Documentation de l'API (Swagger) : http://localhost:8000/docs

Sans clé API ou sans crédit, l'application fonctionne en **mode hors ligne** : lecture structurée des notifications, règles du CDPF et modèle ML ; seules la reformulation par l'IA et la lecture de photos sont désactivées.

Ajouter `?noguide` à l'URL pour ouvrir l'application sans l'onboarding (utile en démo).

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
- LLM : Claude (Anthropic), modèle configurable (`JISER_LLM_MODEL`, par défaut `claude-sonnet-5`).
- Bibliothèques : FastAPI, Pydantic, XGBoost, SHAP, scikit-learn, rank-bm25, pypdf, ReportLab, React, Tailwind CSS, Recharts, lucide-react.
- Données : entièrement synthétiques (aucune donnée réelle de contribuable).

## Limites

- Modèle entraîné sur données synthétiques (règles métier + bruit).
- OTP en mode démonstration : le code est affiché à l'écran ; en production il serait envoyé par SMS ou e-mail.
- Sessions et journal en mémoire (PostgreSQL en production).
- L'IA recommande et explique ; la décision reste humaine.
