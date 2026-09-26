<p align="center">
  <img src="docs/branding/banner.png" alt="JISER · Le pont entre le contribuable et l'administration fiscale" width="100%">
</p>

<p align="center">
  <b>Plateforme d'IA pour le contentieux fiscal tunisien</b><br>
  Hackathon national « IA &amp; Finances publiques » 2026 · Défi principal T3, avec T9, T14 et T20 · <b>Finaliste</b>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11-0b2f5b?logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-REST%20%2B%20WebSocket-0b2f5b?logo=fastapi&logoColor=white">
  <img alt="React" src="https://img.shields.io/badge/React-19-0b2f5b?logo=react&logoColor=white">
  <img alt="XGBoost" src="https://img.shields.io/badge/XGBoost-SHAP-c29a2e">
  <img alt="LLM" src="https://img.shields.io/badge/LLM-OpenAI%20%7C%20Gemini-c29a2e">
  <img alt="RAG" src="https://img.shields.io/badge/RAG-BM25%20%2B%20vecteurs-c29a2e">
  <img alt="Supabase" src="https://img.shields.io/badge/Supabase-PostgreSQL%20%2B%20RLS-2f74c0?logo=supabase&logoColor=white">
  <img alt="n8n" src="https://img.shields.io/badge/n8n-automatisations-2f74c0?logo=n8n&logoColor=white">
  <img alt="Loi 2004-63" src="https://img.shields.io/badge/Donn%C3%A9es-loi%202004--63%20%C2%B7%20INPDP-059669">
</p>

---

## Le problème

Quand l'administration fiscale notifie un redressement, l'entreprise a **45 jours** pour répondre (art. 43 et 44 du CDPF, édition officielle 2024). Sinon, la taxation est établie d'office. La notification est technique : la PME comprend mal ce qu'on lui reproche et répond tard ou mal.

Côté administration, le stock explose. Selon le **ministère des Finances** (rapport annuel de performance 2020) :

| 2020 | Chiffre officiel |
|---|---|
| Affaires de contentieux enrôlées | **5 059** |
| Affaires jugées | **1 139** |
| Dossiers de plus dans le stock en un an | **≈ 3 900** |
| Affaires jugées annulées (souvent pour vice de procédure) | **14,5 %** |
| Durée moyenne d'une vérification | **199 jours** |

Chaque dossier bloqué est une recette fiscale non recouvrée.

## La solution

JISER (جسر, « pont ») relie les deux côtés du litige, en respectant la hiérarchie de l'administration et la confidentialité des contribuables.

| Espace | Pour qui | Ce que JISER apporte |
|---|---|---|
| **Entreprise** | Chef d'entreprise | Notification expliquée chef par chef en français ou en **tounsi**, lecture à voix haute, vices de procédure détectés, articles cités, date limite et rappels, brouillon de réponse, **messagerie en temps réel avec l'agent**, photo depuis le téléphone, **tableau de bord de ses données personnelles**. |
| **Ministre des Finances** | Niveau national | **Pilotage en temps réel avec filtres**, uniquement sur des statistiques anonymes, chiffres officiels, simulateur d'impact. |
| **Chef de centre régional (CRCI)** | Niveau régional | Stock de son centre, **affectation des dossiers**, **validation des conciliations importantes et des comptes de ses agents**. |
| **Chargé(e) du contentieux** | Niveau opérationnel | Dossiers de son centre, score expliqué (SHAP), avis juridique IA, contrôle qualité, copilote, **messagerie avec l'entreprise assistée par l'IA**. |
| **Admin plateforme** | Lien privé | **Validation des comptes**, **veille juridique automatisée**, santé des services, journal d'audit. |

> L'IA recommande et explique. **La décision reste toujours humaine**, et chaque décision est tracée.

## Ce qui distingue JISER

| | |
|---|---|
| 🧠 **3 IA complémentaires** | Règles exactes du CDPF (8 contrôles) · XGBoost + SHAP (AUC 0,84) · LLM ancré dans 305 articles par recherche hybride BM25 + vecteurs |
| 🏛️ **La hiérarchie réelle de l'administration** | Ministre → chef des 27 centres régionaux (CRCI) → chargé du contentieux, chacun avec ses droits, vérifiés côté serveur à chaque requête |
| ✅ **Comptes vérifiés avant accès** | Justificatifs + pré-contrôles automatiques + validation humaine sous 24 h ; les agents sont validés par leur chef de centre |
| 🔒 **Confidentialité dès la conception** | Chiffrement au repos, **pseudonymisation avant toute IA externe**, k-anonymat pour le ministre, accès tracés et visibles par l'entreprise, export et effacement |
| 💬 **Messagerie en temps réel** | WebSocket, accusés de lecture, pièces jointes chiffrées, IA qui résume l'échange, suggère une réponse et liste les pièces manquantes |
| 📡 **Veille juridique automatisée** | Chaque semaine : collecte des textes officiels, détection article par article, validation par un juriste, versions archivées, embeddings recalculés |
| 📊 **Données réelles** | CDPF officiel 2024, statistiques du ministère des Finances, loi de finances 2026 ; simulation calibrée sur les jugements officiels |

---

## Aperçu

### 1. Inscription vérifiée, selon le rôle

| Rôle dans l'administration (hiérarchie et droits) | Justificatifs chiffrés |
|---|---|
| <img src="docs/screenshots/v2/01_onboarding_roles_administration.jpg" alt="Choix du rôle administration"> | <img src="docs/screenshots/v2/03_onboarding_justificatifs.jpg" alt="Justificatifs"> |
| **Demande envoyée : vérification sous 24 h** | **Compte en attente : pré-vérification automatique** |
| <img src="docs/screenshots/v2/04_onboarding_demande_envoyee.jpg" alt="Demande envoyée"> | <img src="docs/screenshots/v2/05_compte_en_attente.jpg" alt="Compte en attente"> |

<details>
<summary><b>Voir la file de validation de l'administrateur</b> (score de pré-vérification, justificatifs, décision motivée)</summary>

<img src="docs/screenshots/v2/06_admin_demandes_acces.jpg" alt="Demandes d'accès">

</details>

### 2. Messagerie en temps réel entreprise ↔ administration

| Côté agent : l'IA liste les pièces manquantes | Côté entreprise : réponse reçue en direct, accusé de lecture |
|---|---|
| <img src="docs/screenshots/v2/08_agent_messagerie_ia.jpg" alt="Messagerie agent"> | <img src="docs/screenshots/v2/09_entreprise_messagerie_temps_reel.jpg" alt="Messagerie entreprise"> |

### 3. Chaque niveau de l'administration a son espace

<img src="docs/screenshots/v2/13_ministre_pilotage_national.jpg" alt="Pilotage national du ministre">

<p align="center"><i>Ministre : pilotage national en temps réel, filtres, statistiques anonymes (groupes de moins de 5 dossiers masqués), chiffres officiels, simulateur.</i></p>

| Chef de centre : équipe, affectations, conciliations à valider | Chargé : stock limité à son centre, « mes dossiers » |
|---|---|
| <img src="docs/screenshots/v2/12_chef_equipe_conciliation.jpg" alt="Équipe et validations"> | <img src="docs/screenshots/v2/10_agent_stock_perimetre.jpg" alt="Stock du centre"> |

<details>
<summary><b>Voir un dossier : score SHAP, avis IA, conciliation soumise au chef de centre</b></summary>

<img src="docs/screenshots/v2/11_agent_conciliation_soumise.jpg" alt="Dossier avec conciliation soumise">

</details>

### 4. Confidentialité : l'entreprise voit et contrôle ses données

<img src="docs/screenshots/v2/16_entreprise_confidentialite.jpg" alt="Confidentialité et mes données">

<p align="center"><i>Ce que reçoit l'IA (identifiants remplacés par des jetons), qui a consulté ses dossiers, consentements, export, suppression, registre des traitements.</i></p>

### 5. Veille juridique automatisée

<img src="docs/screenshots/v2/17_admin_veille_juridique.jpg" alt="Veille juridique">

<p align="center"><i>Pipeline hebdomadaire : 7 modifications réelles détectées dans le Code de la TVA lors de la première exécution, en attente de validation par un juriste (différences mot à mot).</i></p>

### 6. Espace entreprise

| Tableau de bord | Analyse d'une notification | Assistant fiscal IA |
|---|---|---|
| <img src="docs/screenshots/04_entreprise_tableau_de_bord.jpg" alt="Tableau de bord"> | <img src="docs/screenshots/05_entreprise_analyser.jpg" alt="Analyser"> | <img src="docs/screenshots/08_entreprise_assistant.jpg" alt="Assistant"> |

| Sur téléphone : photo de la notification | Analyse en tounsi + brouillon de réponse |
|---|---|
| <img src="docs/screenshots/21_mobile_prendre_photo.jpg" width="240" alt="Photo mobile"> | <img src="docs/screenshots/07_entreprise_analyse_derja_brouillon.jpg" width="420" alt="Analyse en tounsi"> |

<details>
<summary><b>Plus de captures</b> (administration, admin plateforme)</summary>

| Copilote juridique | Contrôle qualité avant envoi |
|---|---|
| <img src="docs/screenshots/15_administration_copilote.jpg" alt="Copilote"> | <img src="docs/screenshots/14_administration_controle_qualite.jpg" alt="Contrôle qualité"> |
| **Pouls de la plateforme** | **Utilisateurs et statuts de vérification** |
| <img src="docs/screenshots/v2/18_admin_vue_ensemble.jpg" alt="Vue d'ensemble"> | <img src="docs/screenshots/v2/19_admin_utilisateurs.jpg" alt="Utilisateurs"> |

</details>

---

## Confidentialité des données (loi organique 2004-63)

| Garantie | Mise en œuvre |
|---|---|
| **Chacun n'accède qu'à son espace** | Permission vérifiée sur chaque route ; rôle relu en base à chaque requête ; dossiers limités au centre de l'agent ; un dossier hors périmètre répond « introuvable » |
| **Comptes vérifiés** | Statut « en attente » : aucun accès avant validation humaine (justificatifs + pré-contrôles) |
| **Chiffrement au repos** | Analyses, réponses, messages, pièces jointes et justificatifs chiffrés (AES + HMAC) ; la clé reste sur le serveur |
| **Pseudonymisation avant l'IA** | Nom, matricule, personnes, e-mails, téléphones, RIB remplacés par des jetons avant tout envoi à OpenAI ou Gemini ; cache pseudonymisé ; synthèse vocale neutralisée |
| **Anonymat des statistiques** | Le ministre ne voit que des agrégats ; groupes de moins de 5 dossiers masqués |
| **Transparence** | L'entreprise voit chaque consultation de ses dossiers (rôle, centre, date) et ce que reçoit l'IA |
| **Droits de la personne** | Consentement séparé pour l'IA (retirable), export complet, droit à l'effacement, registre des traitements |
| **Traçabilité** | Journal d'audit de chaque recommandation IA, décision humaine et consultation |

Détails : **[docs/CONFIDENTIALITE.md](docs/CONFIDENTIALITE.md)**. Tout cela est vérifié par des tests automatiques ([tests/test_securite_acces.py](tests/test_securite_acces.py)).

## Rôles et droits

| Permission | Entreprise | Chargé(e) | Chef de centre | Ministre | Admin |
|---|:-:|:-:|:-:|:-:|:-:|
| Analyser ses notifications, répondre | ✅ | | | | |
| Voir les dossiers nominatifs | | son centre | son centre | ❌ | ❌ |
| Messagerie | avec son agent | ses dossiers | son centre | | |
| Proposer une conciliation | | ✅ | ✅ | | |
| Valider une conciliation > 100 000 DT | | | ✅ | | |
| Affecter les dossiers | | | ✅ | | |
| Valider les comptes | | | ses agents | | tous |
| Tableau de bord | | son centre | son centre | national, anonyme | usage |
| Veille juridique | | | | | ✅ |

---

## Résultats

Mesurés sur 625 dossiers de test jamais vus par le modèle ([`models/metrics.json`](models/metrics.json)) :

| Indicateur | Résultat |
|---|---|
| AUC « chef maintenu devant le juge » | **0,84** |
| AUC « dossier recouvré à plus de 50 % » | **0,82** |
| Montant recouvré en traitant 20 % du stock : tri JISER vs ancienneté | **107,3 MDT vs 28,5 MDT (+276 %)** |
| Répartition des issues simulées vs jugements officiels 2020 | 51,9 / 33,6 / 14,5 % vs 51,5 / 33,9 / 14,5 % |
| Tests de sécurité (accès, isolation, chiffrement, pseudonymisation, droits) | **8/8** |

---

## Architecture

```mermaid
flowchart LR
    U[Entreprise · Chargé · Chef de centre · Ministre · Admin] --> F[React 19 + Vite + Tailwind]
    F -->|REST /api| B[FastAPI]
    F <-->|WebSocket| W[Messagerie temps réel]
    B --> P[Contrôle d'accès<br/>permissions + périmètre]
    P --> R[Règles CDPF]
    P --> M[XGBoost + SHAP]
    P --> G[RAG hybride<br/>BM25 + vecteurs]
    G --> S[Pseudonymisation]
    S --> L[LLM OpenAI · Gemini]
    B --> D[(Supabase<br/>chiffré + RLS)]
    B --> N[(n8n<br/>e-mails)]
    V[Veille juridique<br/>hebdomadaire] --> G
```

Documentation complète : **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

## Données

| Source | Utilisation |
|---|---|
| **CDPF, édition officielle 2024** (jibaya.tn) | Base juridique, règles de procédure, délai de 45 jours |
| Code de la TVA, Code de l'IRPP et de l'IS (Jurisite Tunisie) | Base juridique (RAG), surveillée par la veille |
| **Ministère des Finances, rapport annuel de performance 2020** (gbo.tn) | Chiffres officiels affichés, calibration de la simulation |
| **27 centres régionaux de contrôle des impôts** (ministère des Finances) | Périmètres des chefs de centre et des agents |
| 2 822 dossiers **synthétiques calibrés** | Entraînement du modèle, démonstration |

Les dossiers réels de contribuables sont couverts par le secret fiscal : **aucune donnée réelle de contribuable n'est utilisée**.

---

## Lancer le projet

Prérequis : Python 3.11+, Node.js 20+.

```bash
# 1. Backend
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.txt    # Windows (Linux/Mac : .venv/bin/python)
cp .env.example .env                                                # puis remplir les clés
.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --port 8000

# 2. Frontend (autre terminal)
cd frontend
npm install
npm run dev -- --host                                               # http://localhost:5173

# 3. Tests de sécurité
.venv/Scripts/python -m pytest tests -q
```

- API (Swagger) : http://localhost:8000/docs · Admin plateforme : http://localhost:5173/plateforme
- **Supabase** : exécuter `supabase/schema.sql`, puis `supabase/migration_002_roles_messagerie_confidentialite.sql`, puis `scripts/seed_supabase.py`
- **n8n** : `scripts/build_n8n_workflows.py --cloud`, importer les workflows (code, bienvenue, rappel, **notification**, **veille**)

| Variable | Rôle |
|---|---|
| `OPENAI_API_KEY`, `GEMINI_API_KEY` | IA principale et secours, embeddings, voix |
| `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | Base de données |
| `N8N_*_WEBHOOK_URL`, `N8N_SHARED_SECRET` | E-mails (code, bienvenue, rappels, notifications) |
| `JISER_DATA_KEY` | Clé de chiffrement au repos |
| `ADMIN_EMAILS`, `OFFICIAL_EMAIL_DOMAINS`, `SEUIL_VALIDATION_CONCILIATION` | Accès et règles de gestion |

Sans ces services, l'application reste utilisable : règles et modèle ML à la place de l'IA générative, base en mémoire, codes écrits dans le journal du serveur.

## Documents

| Document | Contenu |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Architecture technique complète |
| [docs/CONFIDENTIALITE.md](docs/CONFIDENTIALITE.md) | Garanties de confidentialité et loi 2004-63 |
| [docs/JISER_note_de_synthese.pdf](docs/JISER_note_de_synthese.pdf) | Note de synthèse (2 pages) |

## Limites

- Modèle entraîné sur des données simulées calibrées : à réentraîner sur l'historique réel de la DGI.
- La vérification des comptes repose sur des justificatifs et une validation humaine ; en production, elle se connecterait au RNE et à l'annuaire de l'administration.
- La veille juridique surveille 3 codes ; les notes communes de la DGI et le JORT restent à ajouter.
- L'IA ne remplace ni l'avocat, ni le conseiller fiscal, ni l'agent : elle explique, recommande et cite ses sources.

---

<p align="center">
  <img src="frontend/public/logo-icon.png" width="56" alt="JISER"><br>
  <sub>JISER · جسر · Le pont entre le contribuable et l'administration fiscale</sub>
</p>
