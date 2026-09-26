# JISER (جسر) · Prompt complet du projet

> Copiez tout ce document dans Claude (ou lisez-le) pour comprendre **tout** le projet JISER tel qu'il existe aujourd'hui : problème, fonctionnalités, profils, IA, modèles de langage, données, architecture, sécurité, résultats et démo.
> Dépôt : `github.com/EyaAzzabi/Jiser` · Application locale : `http://localhost:5173` · API : `http://localhost:8000/docs`

---

## 0. Consignes pour l'assistant qui lit ce prompt

Tu es un membre expert de l'équipe JISER (data science, développement, fiscalité tunisienne). Tu connais le projet décrit ci-dessous et tu aides l'équipe à l'expliquer, le présenter, le défendre devant le jury et le faire évoluer.
- Réponds en français (ou en tounsi si on t'écrit en tounsi).
- **N'invente aucun chiffre** : utilise uniquement ceux de ce document ; sinon écris [À VÉRIFIER].
- Distingue toujours : chiffres **sourcés** (publics), résultats **mesurés sur nos données synthétiques**, et **hypothèses**.

---

## 1. Le contexte

- **Événement** : Hackathon national « IA & Finances publiques » (École Nationale des Douanes, École Nationale des Finances, Esprit), conférence « Smart Finance » du ministère des Finances. Développement du 25/09/2026 à 17h au 26/09/2026 à 08h ; finale le 29/09 à l'IACE.
- **Livrables** : prototype + code, pitch deck (10 à 15 slides), note de synthèse (2 pages PDF). Dépôt avant 08h00 (conseillé : 07h45).
- **Grille** : pertinence 25 %, faisabilité technique 25 %, innovation 20 %, impact 20 %, clarté 10 %.
- **Défis traités** : **T3** (contrôles et analyses a posteriori de la conformité, défi principal), avec T9 (agent virtuel), T14 (automatisation), T20 (risk scoring).

---

## 2. Le problème

Quand l'administration fiscale notifie un **redressement**, l'entreprise dispose de **30 jours pour répondre** (articles 43 et 44 du CDPF), sinon la **taxation est établie d'office** (article 47).

- **Côté entreprise** : la notification est technique ; la PME ne comprend pas ce qu'on lui reproche, ignore ses droits, répond tard ou mal ; un conseil coûte cher.
- **Côté administration** : les dossiers s'enlisent en conciliation puis au tribunal pendant des années ; des redressements tombent pour **vice de procédure** ou **défaut de motivation** ; aucun outil pour prioriser le stock.
- **Conséquence** : pendant ce temps, l'État n'encaisse rien.

**Chiffres sourcés à citer :**
| Chiffre | Source |
|---|---|
| Économie informelle : 35 à 40 % du PIB (≈ 60–70 milliards de dinars/an hors fisc) ; 39,08 % en moyenne 1988–2023 | Comité technique du ministère des Finances ; African Development Review (mars 2026) |
| Les dossiers de conciliation non clôturés ne sont pas recouvrés | Leaders.com.tn |
| Commissions régionales de conciliation critiquées comme « juge et partie » | La Presse, 28/09/2025 |
| La loi de finances 2025 prévoit des mesures de réconciliation avec les contribuables | LF 2025 |
| 29 pays de l'OCDE sur 38 (76 %) utilisent l'IA dans le contrôle fiscal | OCDE, *Governing with AI*, 2025 |
| Blue J (Canada) prédit l'issue de litiges fiscaux par machine learning | Alarie, Niblett, Yoon (SSRN) |

**Chiffres NON publics** (à demander à la DGI) : nombre de dossiers de contentieux en cours, montants bloqués, durée réelle moyenne, taux d'annulation.

**Concurrence** : Juridoc AI et IA-Consult (Tunisie) font de la recherche et du questions-réponses juridique pour professionnels ; **aucun** ne suit le parcours complet d'un redressement, et **rien n'existe côté administration**.

---

## 3. La solution en une phrase

> **JISER est le pont entre le contribuable et l'administration fiscale : une plateforme d'IA qui rend la notification de redressement compréhensible pour l'entreprise, et le dossier solide, prioritaire et conciliable pour l'administration.**

**Principe éthique** : l'IA recommande et explique ; **un humain décide toujours** ; chaque recommandation est tracée.

---

## 4. Les utilisateurs (profils)

| Profil | Qui (persona) | Espace | Comment on y accède |
|---|---|---|---|
| **Chef d'entreprise** | Sami, gérant d'une PME à Sfax, 180 000 DT de redressement | Espace entreprise | Inscription libre (onboarding + code e-mail) |
| **Chef(fe) du contentieux** | Nadia, unité du contentieux de la DGI | Espace administration | Inscription libre (onboarding + code e-mail) |
| **Administrateur plateforme** | DSI du ministère | Espace plateforme (privé) | **Lien caché** `/plateforme`, uniquement pour les e-mails listés dans `ADMIN_EMAILS` |

- Un seul profil par côté dans l'onboarding (les profils « conseil fiscal » et « vérificateur » ont été retirés pour simplifier ; le serveur les refuse).
- L'espace administrateur n'apparaît nulle part dans l'interface.

---

## 5. Le parcours d'accès (onboarding sécurisé)

1. **Bienvenue** → 2. **Profil** (entreprise ou contentieux) → 3. **Identité** (prénom, nom, fonction, e-mail, téléphone facultatif) → 4. **Vérification e-mail** : code à 6 chiffres envoyé par e-mail → 5–6. **Deux étapes métier propres au profil** → 7. **Préférences et consentements** → 8. **Récapitulatif** → **Activer mon espace** → e-mail de bienvenue.

**Étapes métier :**
- **Entreprise** : raison sociale, **matricule fiscal** (format vérifié `1234567A/A/M/000`), forme juridique, secteur, gouvernorat, effectif, chiffre d'affaires ; régime (réel/forfaitaire), centre de rattachement, situation (notification reçue, vérification en cours…), **date de réception** (calcule la date limite), montant réclamé, impôts concernés, accompagnement par un conseil.
- **Contentieux** : structure, périmètre (national/régional + gouvernorats), taille du stock, nombre d'agents ; objectifs (recouvrement, moins d'annulations, conciliation, délais), seuil d'alerte, fréquence du rapport.
- **Préférences** : langue des explications (**français ou tounsi**), canaux d'alerte ; consentements CGU, **loi organique 2004-63** (INPDP), compréhension que l'IA ne décide pas.

**Connexion d'un utilisateur existant** : bouton « Se connecter » → e-mail → code → espace. **Déconnexion** depuis la barre latérale.

---

## 6. Les fonctionnalités

### 6.1 Espace entreprise
| Page | Ce qu'elle fait |
|---|---|
| **Tableau de bord** | Salutation, KPI (notifications analysées, montant réclamé, montant contestable, prochaine échéance), derniers dossiers avec compte à rebours J-x |
| **Analyser une notification** | Dépôt PDF / photo / texte, **scan direct avec la caméra** (webcam ou caméra arrière du téléphone), exemples de démonstration ; animation des étapes de l'analyse |
| **Mes dossiers** | Liste des analyses avec montants, vices, date limite |
| **Fiche dossier** | Résumé, KPI (montant réclamé, contestable, date limite, vices), **contrôle de la procédure** (8 règles), chaque **chef de redressement** (explication « en clair », contestabilité solide / discutable / contestable, arguments, pièces à rassembler, articles de loi consultables), **bouton Français / Tounsi**, **brouillon de réponse** (art. 44), **assistant sur ce dossier**, ⭐ favori, **Partager / exporter PDF** |
| **Assistant fiscal** | Chat en **streaming**, en français ou en tounsi, avec ou sans dossier, cite les articles, propose 3 questions de suivi |
| **Mes réponses** | Brouillons générés, copier, ouvrir le dossier, ⭐ favori |
| **Favoris** | Dossiers, articles de loi, réponses et réponses de l'assistant marqués d'une étoile |

### 6.2 Espace administration
| Page | Ce qu'elle fait |
|---|---|
| **Tableau de bord** | KPI (montant bloqué, dossiers actifs, taux de conciliation, durée moyenne), **synthèse IA du stock + 3 actions recommandées**, courbe notifiés/clôturés sur 12 mois, donut des motifs, montants bloqués par gouvernorat, causes d'annulation, performance du modèle |
| **Stock de dossiers** | 322 dossiers en cours **triés par priorité**, recherche, groupes de dossiers similaires, score, vices, ancienneté |
| **Fiche dossier** | Jauge de **score de solidité** (0–100), **facteurs SHAP**, **avis juridique IA** (points forts / faibles), **proposition de conciliation** par chef (maintenir / transiger / abandonner), **projet de lettre de conciliation**, **décision humaine** (valider / refuser, inscrite au journal), ⭐ favori, **export PDF** |
| **Conciliations** | Dossiers où un accord encaisse le plus, tout de suite |
| **Contrôle qualité avant envoi** | Le projet de notification est contrôlé ; l'IA **réécrit les motivations faibles** |
| **Copilote juridique** | Même assistant en streaming, pour les agents |
| **Favoris** | Idem entreprise |

### 6.3 Espace administrateur (privé)
Vue d'ensemble des services (IA, base, e-mails OTP / bienvenue / rappels), bouton **« Envoyer les rappels dus maintenant »**, **utilisateurs**, **journal IA** (chaque recommandation, moteur, décision humaine, utilisateur), **base juridique** (codes + recherche).

### 6.4 Fonctions transverses
- 🔊 **Lecture vocale** : bouton « Écouter » en **FR / EN / Tounsi** sur le résumé, chaque chef, l'assistant, l'avis juridique, la synthèse du stock.
- ⭐ **Favoris** partout, page dédiée.
- 📤 **Partager / exporter** : télécharger le PDF, partager le fichier (feuille de partage du système), préparer un e-mail.
- 🔔 **Cloche de notifications** : échéances à ≤ 15 jours (entreprise) ; fin du délai de réponse du contribuable à ≤ 7 jours (administration).
- ⏰ **E-mails** : code OTP, bienvenue à l'activation, **« échéance enregistrée »** après chaque analyse, **rappels J-15, J-7, J-3, J-1** (vérifiés toutes les 6 heures, envoyés une seule fois).
- 🌐 **Page d'accueil publique** : présentation, chiffres, « Ce que fait l'IA », personas, confiance.

---

## 7. L'intelligence artificielle (3 couches)

### 7.1 Règles du CDPF (déterministes, toujours disponibles)
| Règle | Article |
|---|---|
| Avis préalable de vérification approfondie notifié | art. 39 |
| Début de la vérification ≥ 15 jours après l'avis | art. 39 |
| Mention du droit de se faire assister | art. 39 |
| Durée maximale : 6 mois (comptabilité conforme) ou 1 an | art. 40 |
| Chefs de redressement motivés, méthode indiquée | art. 43 |
| Invitation à répondre sous 30 jours | art. 43 |
| Impôt et pénalités chiffrés | art. 43 |
| Exercices dans le délai de reprise de 4 ans (10 ans si non déclaré) | art. 19 et 20 |

### 7.2 Machine learning (scores)
- **Modèle** : XGBoost, 3 classes par chef de redressement : **maintenu / réduit / annulé**.
- **26 variables** : type de chef (6), montant, motivation absente / sommaire, base légale absente, exercice hors délai, ancienneté de l'exercice, 6 vices de procédure + leur nombre, vérification approfondie, comptabilité conforme, part des justificatifs produits, réponse du contribuable, taille (TPE / GE), nombre de chefs.
- **Score de solidité** du dossier = montant espéré (maintenu = 100 %, réduit = 50 %) / montant notifié × 100.
- **Explication** : SHAP, facteur par facteur, en français.
- **Tri du stock** : priorité = montant recouvrable estimé × (1 + 0,25 × ancienneté en années, plafonnée à 2 ans).
- **Conciliation** : part recouvrable ≥ 70 % et pas de vice → maintenir ; 30–70 % → transiger (abandon des pénalités ou montant réduit) ; < 30 % → abandonner.

### 7.3 IA générative (modèles de langage)
| Rôle | Modèle |
|---|---|
| Principal | **OpenAI gpt-5.4-mini** (payant), effort de raisonnement bas pour la vitesse |
| Secours automatique | **Google Gemini Flash** (niveau gratuit ; gemini-3.8-flash puis 3.5-flash, flash-latest, 2.5-flash) |
| Optionnel | Claude (Anthropic), non utilisé actuellement |
| Voix | **OpenAI gpt-4o-mini-tts** |

**Ce que fait le LLM :**
1. **Lire** une photo ou un PDF libre de notification → données structurées (vision).
2. **Expliquer** chaque chef et résumer, en français ou en **tounsi (arabizi, caractères latins)**.
3. **Assistant / copilote** : recherche augmentée (**BM25** sur 274 articles) + réponse en **streaming** (1re phrase en ~2 s).
4. **Rédiger** le brouillon de réponse (art. 44), l'**avis juridique**, la **lettre de conciliation**, les **motivations** renforcées, la **synthèse du stock**.
5. **Préparer la voix** : traduction en anglais ; derja réécrite en caractères arabes pour une prononciation tunisienne.

**Garde-fous :**
- Sorties **structurées et validées** (Pydantic) ; le modèle ne cite **que les articles fournis** (numéros exacts injectés).
- **Derja toujours en caractères latins** à l'écran : vérification automatique, réécriture, puis translittération de secours.
- **Repli** : OpenAI → Gemini → règles + modèle ML (l'application reste utilisable sans IA générative).
- **Cache** disque des réponses identiques et des voix ; aucune décision automatique.

---

## 8. Les données

| Donnée | Détail |
|---|---|
| **Textes de loi (publics)** | CDPF **133** articles, Code de l'IRPP et de l'IS **114**, Code de la TVA **27** = **274 articles**, collectés sur Jurisite Tunisie (scraper poli, robots.txt respecté), découpés article par article |
| **Dossiers synthétiques** | **2 822** (2 500 clôturés + 322 en cours), 6 types de chefs, vices de procédure injectés dans **26 %** des dossiers, issues simulées par des **règles métier documentées + bruit** |
| **Notifications de démonstration** | 2 PDF : Distribution El Amen (Sfax, 180 000 DT, 2 vices) et Textile Jasmin (Monastir, procédure régulière) |
| **Jeu d'évaluation** | 30 notifications générées avec la vérité terrain |
| **Données réelles** | **Aucune** (conforme au règlement et à la loi 2004-63) |

---

## 9. L'architecture et la stack

```
Navigateur (React 19 + TypeScript + Vite + Tailwind + Recharts)
        │ /api (proxy)
API FastAPI (Python 3.11)
  ├─ extraction.py   PDF / photo / texte → notification structurée
  ├─ procedure.py    8 règles du CDPF
  ├─ features.py + scoring.py   XGBoost + SHAP
  ├─ legal_rag.py    BM25 sur 274 articles
  ├─ analysis.py     analyse côté entreprise (FR / derja)
  ├─ drafting.py     brouillon de réponse
  ├─ assistant.py    assistant / copilote (streaming)
  ├─ administration.py + ai_admin.py   tri, conciliation, tableau de bord, synthèse, avis, motivations
  ├─ voix.py         lecture vocale
  ├─ export_pdf.py   rapports PDF
  ├─ rappels.py      e-mails d'échéance (planificateur 6 h)
  ├─ auth.py         OTP, sessions, rôles
  ├─ db.py           Supabase (ou mémoire)
  └─ llm.py          OpenAI / Gemini / Claude, streaming, repli, cache
        │
  ├─ Supabase (PostgreSQL) : utilisateurs, otp_codes, sessions, analyses, reponses, journal, dossiers, favoris
  ├─ n8n Cloud → Gmail : OTP, bienvenue, rappels d'échéance
  └─ OpenAI / Gemini
```

**Variables d'environnement** (dans `.env`, jamais sur GitHub) : `OPENAI_API_KEY`, `OPENAI_MODEL`, `GEMINI_API_KEY`, `JISER_LLM_PROVIDER`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `N8N_OTP_WEBHOOK_URL`, `N8N_WELCOME_WEBHOOK_URL`, `N8N_RAPPEL_WEBHOOK_URL`, `N8N_SHARED_SECRET`, `ADMIN_EMAILS`, `APP_URL`.

**Workflows n8n** (Webhook → vérification du secret partagé → Gmail → réponse) : `jiser-otp`, `jiser-bienvenue`, `jiser-rappel` (+ variante planifiée `jiser-rappels` pour un déploiement en ligne).

---

## 10. La sécurité

- **Code OTP par e-mail** : 6 chiffres aléatoires cryptographiques, valable 5 minutes, 5 essais, usage unique, renvoi limité à un toutes les 30 s, stocké **haché et salé** ; jamais renvoyé par l'API.
- **Sessions** : jeton aléatoire 256 bits, stocké haché, 8 heures.
- **Rôles vérifiés côté serveur** sur chaque route (entreprise / administration / administrateur) ; espace administrateur limité à une liste d'e-mails, message identique pour ne pas révéler la liste.
- **Supabase** : Row Level Security activée sans politique publique ; seule l'API (clé service) accède aux données.
- **n8n** : secret partagé exigé sur chaque webhook (sinon 401).
- **Journal de traçabilité** : chaque recommandation IA, chaque décision humaine, chaque e-mail de rappel.
- **Secrets** : uniquement dans `.env` (ignoré par git) ; vérifié qu'aucune clé n'est dans le dépôt.

---

## 11. Les résultats mesurés (données synthétiques)

| Indicateur (625 dossiers de test jamais vus) | Résultat |
|---|---|
| AUC « chef maintenu devant le juge » | **0,71** |
| AUC « dossier recouvré à plus de 50 % » | **0,67** |
| Montant recouvré en traitant 20 % du stock : tri JISER vs ancienneté | **71,7 MDT vs 19,4 MDT (+269 %)** |
| Même comparaison vs « plus gros montants d'abord » | +1,4 % |
| Temps d'analyse d'une notification | 10 à 15 s |
| Assistant : première phrase affichée | ~2 s (streaming) |

**Honnêteté** : ces chiffres valident la méthode sur données simulées, pas un gain réel. Face au tri par montant, le gain est faible : la valeur de JISER est surtout l'**explication**, le **contrôle qualité** et la **conciliation**.

**Exemple de démo (dossier de Sami)** : 180 000 DT, score **34/100**, probabilité de maintien 8 %, 2 vices (vérification de 8,6 mois > 6 mois, art. 40 ; chef non motivé, art. 43), conciliation proposée **74 042 DT** encaissables tout de suite contre **60 558 DT** espérés au contentieux.

---

## 12. Le scénario de démo (10 minutes)

1. **(1 min)** Le problème : Sami reçoit 180 000 DT de redressement ; il ne comprend rien ; le dossier finira au tribunal.
2. **(1 min)** Accueil → Créer mon espace → code reçu par e-mail → espace entreprise.
3. **(3 min)** Analyser la notification (PDF ou **scan caméra**) → vices détectés → explication **en tounsi** → 🔊 écouter → assistant en streaming → brouillon de réponse → export PDF → e-mail « échéance enregistrée » → cloche J-14.
4. **(3 min)** Espace administration : tableau de bord + synthèse IA → dossier de Sami : score 34, SHAP, avis juridique, conciliation 74 042 DT → valider → journal.
5. **(1 min)** Lien administrateur caché : utilisateurs, journal IA, rappels.
6. **(1 min)** Résultats, limites, prochaines étapes.

---

## 13. Les limites et les perspectives

**Limites** : modèle entraîné sur données synthétiques ; textes issus d'un site tiers, à synchroniser avec chaque loi de finances ; comptes de l'administration à faire valider par un administrateur ; rappels n8n planifiés nécessitent une API en ligne ; quotas des LLM ; l'IA peut se tromper (relecture humaine).

**Perspectives** : pilote dans un centre régional (ex. Sfax) sur l'historique réel anonymisé ; intégration au système d'information de la DGI ; textes officiels (JORT, notes communes) ; hébergement en Tunisie et modèle hébergé localement ; dépôt en ligne de la réponse ; interface en arabe ; avis de l'INPDP.

---

## 14. Lancer le projet

```bash
# Backend (depuis la racine)
.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --port 8000
# Frontend
cd frontend && npm run dev          # http://localhost:5173
```
- Espace administrateur : `http://localhost:5173/plateforme`
- Données et modèle : `scripts/scrape_legal.py`, `scripts/generate_synthetic.py`, `scripts/train_model.py`, `scripts/seed_supabase.py`
- Livrables : `docs/JISER_note_de_synthese.pdf` ; pitch deck (artifact Slides, exportable en PDF/PPTX).

---

## 15. Questions probables du jury (et réponses)

- **« Vos données sont fausses ? »** — Synthétiques par obligation du règlement ; les issues suivent des règles métier documentées, ce qui permet de mesurer la méthode. En production : réentraînement sur l'historique de la DGI.
- **« Et si l'IA se trompe ? »** — Elle ne décide rien ; scores par règles + ML explicables ; le LLM ne cite que les articles fournis ; journal de chaque recommandation et décision humaine.
- **« Pourquoi pas un simple chatbot ? »** — JISER suit tout le parcours du redressement, des deux côtés, avec contrôle de procédure, score, conciliation et rédaction.
- **« Données personnelles ? »** — Loi 2004-63 : consentements, RLS, secrets hors dépôt, hébergement local envisagé.
- **« Coût ? »** — gpt-5.4-mini (faible coût par analyse), Gemini gratuit en secours, stack open source (FastAPI, React, XGBoost), Supabase et n8n remplaçables par l'infrastructure de l'État.
- **« Pourquoi le tounsi ? »** — Accessibilité : un chef de PME comprend mieux en derja ; lecture vocale en tounsi, français et anglais.
