# JISER (جسر) · Prompt complet du projet (version finale)

> Copiez tout ce document dans un assistant IA (ou lisez-le) pour comprendre **tout** le projet JISER tel qu'il existe aujourd'hui : problème, profils et droits, fonctionnalités, IA, confidentialité, données, architecture, sécurité, résultats, démo et questions du jury.
> Dépôt : `github.com/EyaAzzabi/Jiser` · Application locale : `http://localhost:5173` · API : `http://localhost:8000/docs`
> Documents détaillés : `README.md`, `docs/ARCHITECTURE.md`, `docs/CONFIDENTIALITE.md`, `docs/JISER_note_de_synthese.pdf`.

---

## 0. Consignes pour l'assistant qui lit ce prompt

Tu es un membre expert de l'équipe JISER (data science, développement, fiscalité tunisienne). Tu aides l'équipe à expliquer, présenter, défendre et faire évoluer le projet.
- Réponds en français (ou en arabe si on t'écrit en arabe).
- **N'invente aucun chiffre** : utilise uniquement ceux de ce document ; sinon écris [À VÉRIFIER].
- Distingue toujours : chiffres **officiels** (ministère des Finances), résultats **mesurés sur nos données synthétiques calibrées**, et **hypothèses**.

---

## 1. Le contexte

- **Événement** : Hackathon national « IA & Finances publiques ». Prototype développé du 25/09/2026 17 h au 26/09/2026 8 h. **L'équipe est présélectionnée pour la finale (2e sur 30 au premier classement)**. Finale le 29/09/2026.
- **Grille** : pertinence 25 %, faisabilité technique 25 %, innovation 20 %, impact 20 %, clarté 10 %.
- **Défis traités** : **T3** (contrôles et analyses a posteriori de la conformité, défi principal), avec T9 (agent virtuel), T14 (automatisation), T20 (risk scoring).
- **Retours du jury intégrés pour la finale** : vérification des comptes avant accès, gestion sécurisée des utilisateurs (chacun son espace), hiérarchie de l'administration avec rôles et droits, messagerie en temps réel, confidentialité des données (équivalent RGPD), mise à jour automatique de la base juridique et de ses embeddings.

---

## 2. Le problème

Quand l'administration fiscale notifie un **redressement**, l'entreprise a **45 jours pour répondre** (articles 43 et 44 du CDPF, édition officielle 2024 ; le délai est passé de 30 à 45 jours avec la loi de finances 2015). Sinon, la taxation est établie d'office.

- **Côté entreprise** : la notification est technique ; la PME ne comprend pas ce qu'on lui reproche, ignore ses droits, répond tard ou mal.
- **Côté administration** : le stock de contentieux grossit, des redressements tombent pour vice de procédure ou défaut de motivation, et rien n'aide à prioriser.

**Chiffres officiels** (ministère des Finances, rapport annuel de performance 2020, mission « Finances », gbo.tn) :

| 2020 | Valeur |
|---|---|
| Affaires de contentieux enrôlées | **5 059** |
| Affaires jugées | **1 139** |
| Dossiers de plus dans le stock en un an | **≈ 3 900** |
| Affaires jugées annulées | **14,5 %** |
| Durée moyenne d'une vérification | **199 jours** |
| Montants confirmés en première instance | **71,8 %** |

Autres repères : recettes fiscales de 47 773 MD prévues par la loi de finances 2026 ; 29 pays de l'OCDE sur 38 utilisent l'IA dans le contrôle fiscal (OCDE, 2025).

**Concurrence** : Juridoc AI et IA-Consult (Tunisie) font de la recherche juridique pour professionnels ; **aucun** ne suit le parcours complet d'un redressement, et **rien n'existe côté administration**.

---

## 3. La solution en une phrase

> **JISER est le pont entre le contribuable et l'administration fiscale : une plateforme d'IA qui rend la notification compréhensible pour l'entreprise, et le dossier solide, prioritaire et conciliable pour l'administration, dans le respect de sa hiérarchie et de la confidentialité des contribuables.**

**Principe éthique** : l'IA recommande et explique ; **un humain décide toujours** ; chaque recommandation, décision et consultation est tracée.

---

## 4. Les profils, leurs droits et leurs périmètres

La hiérarchie suit l'organisation réelle : **ministère des Finances → Direction générale des impôts → 27 centres régionaux de contrôle des impôts (CRCI)**, 16 de catégorie A et 11 de catégorie B → agents.

| Profil | Persona | Ce qu'il voit | Ce qu'il peut faire |
|---|---|---|---|
| **Chef d'entreprise** | Sami, gérant d'une PME à Sfax, 180 000 DT de redressement | Ses propres dossiers | Analyser, comprendre, répondre, échanger avec l'agent, gérer ses données |
| **Ministre des Finances** | Cabinet du ministre | Statistiques **nationales et anonymes** (groupes de moins de 5 dossiers masqués) | Pilotage en temps réel avec filtres, simulateur, chiffres officiels ; **aucun dossier nominatif** |
| **Chef de centre régional** | Leila, CRCI Sfax 1 | Dossiers de son centre | Affecter les dossiers, **valider les conciliations > 100 000 DT**, **valider les comptes de ses agents** |
| **Chargé(e) du contentieux** | Mehdi, CRCI Sfax 1 | Dossiers de son centre (d'abord ceux qui lui sont affectés) | Score, avis IA, contrôle qualité, copilote, messagerie, proposer une conciliation |
| **Administrateur plateforme** | DSI | Usage de la plateforme | Valider les comptes, piloter la veille juridique, journal d'audit ; accès par **lien caché** `/plateforme` réservé à `ADMIN_EMAILS` |

- Chaque route de l'API vérifie une **permission**. Le **rôle est relu en base à chaque requête**, jamais pris dans le navigateur.
- Un dossier hors périmètre répond « introuvable » (404) : on ne peut pas savoir qu'il existe.

---

## 5. L'inscription et la vérification des comptes

1. **Bienvenue**.
2. **Profil** : Entreprise ou Administration.
3. Si Administration : **choix du rôle**, avec la hiérarchie et les droits de chaque niveau.
4. **Identité** : pour l'administration, une adresse officielle est attendue.
5. **Code à 6 chiffres** reçu par e-mail.
6. **Étapes métier** :
   - entreprise : raison sociale, matricule fiscal au format vérifié, secteur, gouvernorat, régime, date de réception…
   - administration : centre (liste des 27 CRCI), matricule d'agent, grade…
7. **Justificatifs**, chiffrés :
   - entreprise : extrait du registre national des entreprises (RNE) et CIN du gérant ;
   - agent : carte professionnelle ;
   - chef de centre ou ministre : décision ou décret de nomination.
8. **Consentements** : conditions d'utilisation ; données personnelles (loi 2004-63) ; IA générative séparément et facultative.
9. **Récapitulatif**, puis **« Demande envoyée »**.

**Vérification (sous 24 h)** :
- **Pré-contrôles automatiques** avec un score :
  - pièces déposées ;
  - format du matricule ;
  - doublon ;
  - **raison sociale et matricule retrouvés dans l'extrait RNE** (lecture locale du PDF ; les images ne partent jamais vers une IA) ;
  - adresse officielle pour l'administration ;
  - un seul ministre actif.
- **Validation humaine** : un agent est validé par **le chef de son centre** ; les autres profils par l'administrateur.
- **E-mails** : « demande reçue », « compte activé », « demande refusée » (avec le motif).
- Tant que le compte n'est pas actif, l'utilisateur ne voit que sa page de suivi, rafraîchie automatiquement.

---

## 6. Les fonctionnalités

### 6.1 Espace entreprise
| Page | Ce qu'elle fait |
|---|---|
| **Tableau de bord** | KPI (notifications, montant réclamé, montant contestable, prochaine échéance), derniers dossiers avec J-x |
| **Analyser** | Dépôt PDF / photo / texte ; **« Prendre une photo »** sur téléphone ; scan à l'écran ; exemples |
| **Fiche dossier** | Résumé ; **8 contrôles de procédure** ; chaque chef (explication claire, contestabilité, arguments, pièces à réunir, articles consultables) ; **français / العربية** ; brouillon de réponse (art. 44, en français) ; assistant ; **« Écrire à l'administration »** ; favori ; export PDF |
| **Messagerie** | Échange **en temps réel** avec l'agent du dossier : pièces jointes chiffrées, accusés de lecture, IA (résumé, réponse suggérée, pièces manquantes) |
| **Assistant fiscal** | Chat en streaming, **français ou arabe standard**, cite les articles |
| **Mes réponses, Favoris** | Brouillons, éléments marqués d'une étoile |
| **Confidentialité** | **Ce que voit l'IA** (données remplacées par des jetons), **qui a consulté mes dossiers**, consentements, export de toutes mes données, suppression du compte, registre des traitements |

### 6.2 Espace administration (selon le rôle)
| Page | Rôles | Ce qu'elle fait |
|---|---|---|
| **Pilotage national** | Ministre | Temps réel (actualisé toutes les 10 s), filtres (gouvernorats, motifs, étape, montant, période), carte du stock, flux entrées/sorties, activité 24 h, chiffres officiels, **simulateur d'impact** |
| **Tableau de bord** | Chef, agent | Stock de son centre, synthèse IA, chiffres officiels, simulateur |
| **Stock de dossiers** | Chef, agent | Tri par priorité, « Mes dossiers affectés », colonne « Affecté à » |
| **Fiche dossier** | Chef, agent | Score de solidité, facteurs SHAP, avis juridique IA, conciliation par chef, lettre ; au-delà de 100 000 DT, la validation d'un agent est **soumise au chef de centre** |
| **Équipe et validations** | Chef | Conciliations à valider, charge de l'équipe, affectation des dossiers, comptes d'agents à valider |
| **Messagerie** | Chef, agent | Conversations des entreprises de son centre |
| **Conciliations, Contrôle qualité, Copilote** | Chef, agent (copilote aussi pour le ministre) | Comme en v1 |

### 6.3 Espace administrateur plateforme
Pouls de la plateforme, santé des services, **demandes d'accès** (pré-contrôles, justificatifs, décision motivée), utilisateurs et statuts, journal IA, base juridique, **veille juridique**.

### 6.4 Fonctions transverses
- 🔊 **Voix** : « Écouter » en français, anglais ou **arabe standard**.
- 🔔 **Cloche** : échéances (entreprise), fins de délai et conciliations à valider (administration).
- ⏰ **E-mails** (n8n) : code, bienvenue, échéance enregistrée, rappels J-15/J-7/J-3/J-1, décisions de compte, alerte de nouveau message (**sans le contenu**).
- ⭐ Favoris, 📤 export PDF et partage, 📱 utilisable sur téléphone.

---

## 7. L'intelligence artificielle

### 7.1 Règles du CDPF (déterministes, toujours disponibles, en français et en arabe)
| Règle | Article |
|---|---|
| Avis préalable de vérification approfondie | art. 39 |
| Début ≥ 15 jours après l'avis | art. 39 |
| Mention du droit de se faire assister | art. 39 |
| Durée maximale : 6 mois (comptabilité conforme) ou 1 an | art. 40 |
| Chefs motivés, méthode indiquée | art. 43 |
| Invitation à répondre sous **45 jours** | art. 43-44 |
| Impôt et pénalités chiffrés | art. 43 |
| Délai de reprise de 4 ans (10 ans si non déclaré) | art. 19-20 |

### 7.2 Machine learning
- **XGBoost** 3 classes par chef (maintenu / réduit / annulé), **26 variables**, explications **SHAP**.
- **Score de solidité** (0 à 100) et montant recouvrable par dossier.
- **Tri du stock** : montant recouvrable estimé × (1 + 0,25 × ancienneté, plafonnée à 2 ans).
- **Conciliation** : part recouvrable ≥ 70 % sans vice → maintenir ; 30 à 70 % → transiger ; < 30 % → abandonner.

### 7.3 IA générative
| Rôle | Modèle |
|---|---|
| Principal | OpenAI **gpt-5.4-mini** |
| Secours automatique | Google **Gemini Flash** |
| Voix | OpenAI **gpt-4o-mini-tts** |
| Embeddings | OpenAI **text-embedding-3-small** |

Le LLM sert à :
1. lire une photo ou un PDF ;
2. expliquer et résumer en **français ou en arabe standard (الفصحى)**, avec la terminologie officielle (« الفصل 44 من مجلة الحقوق والإجراءات الجبائية », « التوظيف الإجباري ») ;
3. faire fonctionner l'assistant et le copilote ;
4. rédiger le brouillon de réponse, l'avis juridique, la lettre de conciliation, les motivations et la synthèse du stock ;
5. aider dans la messagerie : résumé, réponse suggérée, pièces manquantes.

**Recherche hybride (RAG)** sur **305 articles** :
- BM25 (mots exacts) + similarité vectorielle (sens), fusionnés par rang.
- Exemple mesuré : pour la question « ما هو أجل الرد على الإعلام بنتائج المراجعة؟ », la recherche hybride trouve l'**article 44** en premier. BM25 seul ne trouve **aucun** article, car les codes sont en français.

**Garde-fous** :
- Sorties structurées validées.
- Le modèle ne cite que les articles fournis.
- **Pseudonymisation** avant tout appel (voir § 8).
- Repli OpenAI → Gemini → règles + ML.
- Aucune décision automatique.

---

## 8. La confidentialité des données (loi organique 2004-63, INPDP)

| Garantie | Mise en œuvre |
|---|---|
| Chacun son espace | Permission sur chaque route, rôle relu en base, périmètre du centre |
| Comptes vérifiés | Aucun accès avant validation humaine |
| Chiffrement au repos | Analyses, réponses, messages, pièces jointes, justificatifs (Fernet : AES + HMAC) ; clé côté serveur |
| **Pseudonymisation avant l'IA** | Nom, matricule, personnes, e-mails, téléphones, RIB, CIN remplacés par des jetons (`[ENTREPRISE_1]`) avant OpenAI ou Gemini ; cache pseudonymisé ; voix neutralisée |
| Anonymat des statistiques | Ministre : agrégats seulement, groupes < 5 dossiers masqués (k-anonymat) |
| Transparence | L'entreprise voit chaque consultation de ses dossiers (rôle, centre, date) et ce que reçoit l'IA |
| Droits | Consentement IA retirable (JISER passe alors en règles + ML), export complet, effacement, registre des traitements |
| Traçabilité | Journal de chaque recommandation, décision et consultation |

Le tout est vérifié par **8 tests automatiques** (`tests/test_securite_acces.py`).

---

## 9. La veille juridique automatisée

1. **Chaque semaine**, le planificateur interne du backend lance le pipeline (le bouton « Lancer la veille maintenant » aussi).
2. **Collecte** des sources : CDPF officiel (jibaya.tn), Codes TVA et IRPP/IS (Jurisite).
3. **Détection** : empreinte SHA-256 de chaque source.
4. **Découpage** article par article.
5. **Comparaison** avec la base : ajout, modification ou abrogation.
6. **Validation humaine** de chaque changement.
7. **Publication** : l'ancienne version est archivée avec ses dates.
8. **Embeddings** : recalculés pour les articles modifiés.
9. **Rapport** envoyé par e-mail.

**Première exécution réelle** : CDPF et IRPP/IS identiques ; **7 écarts dans le Code de la TVA**. Après revue :
- **4 articles publiés** (art. 3, 4, 5 et 20 : l'ancienne base contenait par erreur des articles de la loi de promulgation) ;
- **3 rejetés** avec motif (art. 2 et 6 : extraits tronqués ; art. 13 : à vérifier au JORT).

Revue assistée par IA, **à confirmer par un juriste**. Une simulation marquée permet de démontrer le circuit sans modifier la base.

---

## 10. Les données

| Donnée | Détail |
|---|---|
| **Textes de loi** | CDPF édition officielle 2024 (154 articles + 10 complétés), Code de la TVA (27), Code de l'IRPP et de l'IS (114) = **305 articles**, versionnés |
| **Chiffres officiels** | RAP 2020 du ministère des Finances, loi de finances 2026 |
| **Dossiers** | **2 822 synthétiques calibrés** sur la répartition officielle des jugements 2020 : simulation 51,9 / 33,6 / 14,5 % contre 51,5 / 33,9 / 14,5 % officiel ; recouvrement 70 % contre 71,8 % |
| **Données réelles de contribuables** | **Aucune** (secret fiscal, loi 2004-63) |

---

## 11. L'architecture

```
Navigateur (React 19 + Vite + Tailwind + Recharts ; polices Inter, Poppins, Tajawal pour l'arabe)
   │ REST /api                     │ WebSocket /api/messagerie/ws
API FastAPI (Python 3.11)
  ├─ deps.py            session · statut du compte · rôle relu en base · permission · journal des accès
  ├─ routers/           comptes · pilotage · messagerie · confidentialité · veille
  ├─ services/
  │   ├─ permissions    rôles, 27 CRCI, périmètres        ├─ securite     chiffrement, pseudonymisation, consentement
  │   ├─ comptes        pré-contrôles, validation          ├─ messagerie   conversations, hub temps réel, IA
  │   ├─ pilotage       agrégats k-anonymes, affectations  ├─ veille       pipeline, versions, embeddings
  │   ├─ procedure      8 règles (FR/AR)                   ├─ scoring      XGBoost + SHAP
  │   ├─ legal_rag      BM25 + vecteurs                    ├─ analysis, assistant, drafting, ai_admin, administration
  │   └─ llm, voix, auth, db (chiffrement à l'écriture), rappels, export_pdf, extraction
  ├─ Supabase (PostgreSQL + RLS, aucune politique publique)
  ├─ n8n Cloud → Gmail : code, bienvenue, rappels, notifications
  └─ OpenAI · Gemini
```

**Supabase** : `schema.sql`, puis `migration_002_roles_messagerie_confidentialite.sql`. Tables :
- `utilisateurs` (statut, vérification) ;
- `pieces_justificatives`, `affectations`, `conciliations`, `conversations`, `messages`, `acces` ;
- `analyses`, `reponses`, `journal`, `dossiers`, `favoris`, `otp_codes`, `sessions`.

**Variables d'environnement** (`.env`, jamais sur GitHub) :
- IA : `OPENAI_API_KEY`, `GEMINI_API_KEY` ;
- base : `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` ;
- e-mails : `N8N_*_WEBHOOK_URL`, `N8N_SHARED_SECRET` ;
- chiffrement : `JISER_DATA_KEY` ;
- accès et règles : `ADMIN_EMAILS`, `OFFICIAL_EMAIL_DOMAINS`, `SEUIL_VALIDATION_CONCILIATION`, `APP_URL`.

---

## 12. La sécurité

- Code à usage unique par e-mail : 6 chiffres, 5 minutes, 5 essais, haché et salé.
- Sessions : jeton de 256 bits haché, valable 8 h.
- Contrôle d'accès par permission et par périmètre.
- Comptes validés avant accès.
- Espace administrateur caché.
- Webhooks n8n protégés par un secret partagé.
- WebSocket authentifié par le premier message (le jeton n'est jamais dans l'URL).
- Secrets uniquement dans `.env`.

---

## 13. Les résultats mesurés

| Indicateur (625 dossiers de test jamais vus) | Résultat |
|---|---|
| AUC « chef maintenu devant le juge » | **0,84** |
| AUC « dossier recouvré à plus de 50 % » | **0,82** |
| Recouvré en traitant 20 % du stock : tri JISER vs ancienneté | **107,3 MDT vs 28,5 MDT (+276 %)** |
| Même comparaison vs « plus gros montants d'abord » | +2,4 % |
| Tests de sécurité | **8/8** |

**Dossier de démo (Sami, Distribution El Amen, Sfax)** :
- 180 000 DT réclamés, réponse attendue avant le **04/10/2026** ;
- **score 47/100**, probabilité de maintien 17 % ;
- 2 vices : durée de vérification de 7,9 mois au lieu de 6 (art. 40), chef C3 non motivé (art. 43) ;
- conciliation proposée : **102 721 DT** encaissables tout de suite, contre **84 721 DT** espérés au contentieux dans plusieurs années.

**Honnêteté** : ces chiffres valident la méthode sur des données simulées calibrées, pas un gain réel. Face au tri par montant, le gain est faible : la valeur de JISER est surtout l'explication, le contrôle qualité, la conciliation et la relation sécurisée entre les deux côtés.

---

## 14. Le scénario de démo (10 minutes)

1. **(1 min) Le problème** : 5 059 affaires entrées en 2020 contre 1 139 jugées ; Sami reçoit 180 000 DT de redressement.
2. **(2 min) Inscription vérifiée** : Administration → choix du rôle (hiérarchie) ; Entreprise → justificatifs → « demande envoyée » → l'administrateur valide (pré-contrôle 100 %) → e-mail.
3. **(2 min) Entreprise** :
   - photo de la notification → vices détectés → explication **en arabe** → 🔊 écoute ;
   - **Confidentialité** : « ce que voit l'IA » ;
   - « Écrire à l'administration ».
4. **(2 min) Agent et chef de centre** :
   - le message arrive **en direct** ; l'IA liste les pièces manquantes ; l'agent répond ;
   - l'agent valide la conciliation de 102 721 DT → **soumise au chef de centre**, qui la valide.
5. **(1 min) Ministre** : pilotage national en temps réel, filtres, groupes masqués ; accès nominatif refusé.
6. **(1 min) Veille juridique** : 7 écarts détectés, différences mot à mot, validation, versions archivées.
7. **(1 min) Résultats, limites, feuille de route.**

---

## 15. Les limites et les perspectives

**Limites** :
- modèle entraîné sur des données simulées calibrées ;
- chiffres officiels détaillés les plus récents : 2020 ;
- vérification d'identité par justificatifs et validation humaine, pas encore reliée au RNE ;
- veille limitée à 3 codes ; jurisprudence non intégrée ;
- hub temps réel mono-serveur.

**Perspectives** :
- pilote dans un CRCI (ex. Sfax 1) sur l'historique réel anonymisé ;
- connexion au RNE et à l'annuaire de l'administration ;
- hébergement en Tunisie et LLM hébergé localement ;
- veille élargie (JORT, notes communes, lois de finances) ;
- déclaration à l'INPDP.

---

## 16. Lancer le projet

```bash
.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --port 8000   # API
cd frontend && npm run dev -- --host                                         # http://localhost:5173
.venv/Scripts/python -m pytest tests -q                                      # 8 tests de sécurité
```
- Espace administrateur : `http://localhost:5173/plateforme`.
- Avant le premier lancement de cette version : exécuter la migration Supabase 002.
- Sur téléphone : même Wi-Fi, adresse « Network » affichée par Vite.

---

## 17. Questions probables du jury (et réponses)

- **« Vos données sont fausses ? »** Les dossiers individuels sont couverts par le secret fiscal. Nos dossiers simulés sont **calibrés sur les jugements officiels 2020** ; les chiffres affichés du ministère sont réels. En production : réentraînement sur l'historique de la DGI.
- **« Qui peut voir les données d'une entreprise ? »** Uniquement l'agent de son centre en charge du dossier et son chef de centre. Ni le ministre (statistiques anonymes) ni l'administrateur. L'entreprise voit chaque consultation.
- **« Vous envoyez des données fiscales à OpenAI ? »** Non : les identifiants sont remplacés par des jetons avant l'envoi ; l'entreprise peut le vérifier dans « Confidentialité » et retirer son consentement.
- **« Comment savez-vous que la personne est bien le gérant, ou un agent ? »** Justificatifs, pré-contrôles automatiques (dont la concordance avec l'extrait RNE) et validation humaine ; un agent est validé par son chef de centre.
- **« Et quand la loi change ? »** La veille hebdomadaire détecte les articles modifiés, un humain valide, l'ancienne version est archivée et les embeddings sont recalculés. La première exécution a trouvé 7 écarts réels.
- **« Et si l'IA se trompe ? »** Elle ne décide rien : les scores reposent sur des règles et du ML explicables, le LLM ne cite que les articles fournis, et chaque recommandation et décision est journalisée.
- **« Pourquoi l'arabe standard ? »** C'est la langue officielle des textes et de l'administration, compréhensible partout ; la terminologie officielle est respectée, avec lecture vocale.
- **« Coût ? »** gpt-5.4-mini à faible coût par analyse, Gemini gratuit en secours, stack open source ; Supabase et n8n sont remplaçables par l'infrastructure de l'État.
