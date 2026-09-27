# JISER · Pitch deck final

Finale du Hackathon national « IA & Finances publiques », 29 septembre 2026, IACE.

**Format** : 14 slides, **7 minutes de pitch**, dont 3 minutes de démonstration en direct (slide 10), puis questions du jury.
- Si le temps accordé est de **5 minutes** : fusionner les slides 2 et 3, réduire la démo à 2 minutes, retirer la slide 8.
- **Identité visuelle** : bleu marine `#0b2f5b`, or `#c29a2e`, bleu pont `#2f74c0` ; titres en Poppins, texte en Inter, arabe en Tajawal ; logo JISER en haut à gauche de chaque slide.
- **Règle d'or** : une idée par slide, le texte à l'écran reste court, le détail est dans la voix.

Critères du jury : pertinence 25 %, faisabilité technique 25 %, innovation 20 %, impact 20 %, clarté 10 %. La colonne « critère » indique ce que chaque slide sert.

---

## Slide 1 · Titre (15 s)

**À l'écran**
- Grand logo JISER · جسر
- « Le pont entre le contribuable et l'administration fiscale »
- Sous-titre : « L'IA qui rend le contentieux fiscal compréhensible, rapide et équitable, des deux côtés »
- Bas de slide : noms de l'équipe · Défi T3 (+ T9, T14, T20)

**Visuel** : la bannière `docs/branding/banner.png`.

**Notes de l'orateur**
> « Bonjour. Nous sommes l'équipe JISER, جسر, "le pont". Nous avons construit le pont qui manque entre le contribuable et l'administration fiscale, au moment le plus tendu de leur relation : le redressement. »

---

## Slide 2 · Le problème, vu par une entreprise (40 s) · *pertinence*

**À l'écran**
- « Sami, gérant d'une PME à Sfax, reçoit une notification de redressement : **180 000 DT** »
- « Il a **45 jours** pour répondre (art. 43-44 du CDPF), sinon : taxation d'office »
- Trois icônes : ❓ ne comprend pas ce qu'on lui reproche · ⚖️ ignore ses droits · ⏳ répond trop tard, ou mal

**Visuel** : photo d'une notification papier (capture `docs/screenshots/v2/22_mobile_pages_photographiees.jpg` recadrée).

**Notes de l'orateur**
> « Sami reçoit ce document. Il est technique, plein d'articles de loi. Il ne sait pas s'il a raison de contester, ni comment. Un conseil coûte cher. Et au bout de 45 jours, c'est la taxation d'office. Des milliers de PME tunisiennes vivent exactement cela. »

---

## Slide 3 · Le problème, vu par l'État (40 s) · *pertinence, impact*

**À l'écran** : les chiffres officiels du **ministère des Finances** (rapport annuel de performance 2020)

| | |
|---|---|
| **5 059** | affaires de contentieux enrôlées en 2020 |
| **1 139** | affaires jugées |
| **+3 900** | dossiers de plus dans le stock chaque année |
| **14,5 %** | des affaires jugées annulées, souvent pour vice de procédure |
| **199 jours** | durée moyenne d'une vérification |

Source en petit : RAP 2020, mission « Finances », gbo.tn.

**Visuel** : le graphique « entrées vs jugements » de l'espace administration (capture `13_ministre_pilotage_national`, bloc « La réalité officielle »).

**Notes de l'orateur**
> « Côté administration, ce n'est pas mieux. Chaque année, on ouvre quatre fois plus de dossiers qu'on n'en juge : le stock grandit de près de 4 000 dossiers par an. Et une affaire sur sept est annulée, souvent pour une erreur de procédure. Chaque dossier bloqué, c'est une recette qui n'entre pas dans les caisses de l'État. »

---

## Slide 4 · Ce qui manque aujourd'hui (20 s) · *innovation*

**À l'écran**
- Les outils existants (Juridoc AI, IA-Consult) = recherche juridique **pour professionnels**
- **Personne** ne suit le redressement de bout en bout
- **Rien** n'existe pour l'administration : ni tri du stock, ni contrôle qualité, ni conciliation assistée
- Et surtout : **aucun canal sécurisé** entre les deux parties

**Notes de l'orateur**
> « Il existe des moteurs de recherche juridique pour les avocats. Mais personne n'accompagne l'entreprise du premier courrier à la réponse, personne n'outille l'administration, et les deux côtés ne se parlent que par courrier. »

---

## Slide 5 · La solution : JISER (30 s) · *pertinence*

**À l'écran** : un schéma en pont
- À gauche, **Entreprise** : comprendre · vérifier · répondre
- Au centre, **JISER** : IA explicable · confidentialité · traçabilité
- À droite, **Administration** : prioriser · sécuriser · concilier
- Sous le pont : « L'IA recommande et explique. **L'humain décide toujours.** »

**Notes de l'orateur**
> « JISER est une seule plateforme pour les deux côtés du litige. L'entreprise comprend et répond dans les délais. L'administration traite d'abord les bons dossiers, avec des notifications solides, et règle à l'amiable ce qui doit l'être. L'IA recommande, explique et cite la loi ; la décision reste toujours humaine. »

---

## Slide 6 · Côté entreprise (35 s) · *pertinence, innovation*

**À l'écran** : 4 captures en ligne, légendées
1. 📱 **Photo de la notification**, page par page → lue en 6 s
2. 🔍 **8 contrôles de procédure** du CDPF → vices détectés
3. 🗣️ **Explications en français ou en arabe standard**, lecture à voix haute
4. ✍️ **Brouillon de réponse** + 💬 **messagerie en temps réel** avec l'agent

**Visuels** : `22_mobile_pages_photographiees`, `20_entreprise_analyse_arabe`, `09_entreprise_messagerie_temps_reel`.

**Notes de l'orateur**
> « Sami photographie sa notification avec son téléphone. En quelques secondes, JISER vérifie la procédure article par article, explique chaque redressement en français ou en arabe, et prépare sa réponse. S'il a une question, il écrit directement à l'agent qui traite son dossier, dans une messagerie sécurisée. »

---

## Slide 7 · Côté administration, dans le respect de la hiérarchie (40 s) · *pertinence, faisabilité*

**À l'écran** : pyramide à 3 niveaux
- **Ministre** : pilotage national **en temps réel**, statistiques anonymes
- **Chef de centre (27 CRCI)** : affecte les dossiers, **valide les conciliations > 100 000 DT** et les comptes de ses agents
- **Chargé du contentieux** : dossiers de son centre, triés par montant recouvrable, score expliqué, avis juridique IA, contrôle qualité avant envoi

Encadré : « Chaque niveau voit **uniquement** ce que ses droits autorisent, vérifié à chaque requête. »

**Visuels** : `13_ministre_pilotage_national`, `12_chef_equipe_conciliation`, `10_agent_stock_perimetre`.

**Notes de l'orateur**
> « JISER respecte la hiérarchie réelle de l'administration fiscale. Le ministre pilote le contentieux national en temps réel, sans jamais voir le nom d'un contribuable. Le chef de centre affecte les dossiers et valide les conciliations importantes. L'agent travaille sur les dossiers de son centre, triés par ce qu'ils peuvent rapporter, avec un score expliqué. »

---

## Slide 8 · Une IA digne de confiance (30 s) · *faisabilité technique, innovation*

**À l'écran** : 3 colonnes
- ⚖️ **Règles du CDPF** : 8 contrôles exacts, toujours disponibles
- 📈 **Machine learning** : XGBoost + SHAP, chaque score expliqué facteur par facteur
- 🧠 **IA générative ancrée dans la loi** : recherche hybride sur **305 articles**, ne cite que les articles retrouvés

Bandeau : 📡 **Veille juridique automatique** : chaque semaine, les textes officiels sont comparés article par article. **Première exécution : 7 écarts réels détectés dans le Code de la TVA.**

**Visuel** : `17_admin_veille_juridique` (différences mot à mot).

**Notes de l'orateur**
> « Nous n'avons pas mis un chatbot sur un problème juridique. Trois couches : des règles exactes pour la procédure, un modèle de machine learning explicable pour les scores, et une IA générative qui ne cite que les articles de loi qu'elle a retrouvés. Et parce que la loi change à chaque loi de finances, JISER la surveille seul chaque semaine. À sa première exécution, il a trouvé 7 écarts réels dans le Code de la TVA, que nous avons fait valider avant publication. »

---

## Slide 9 · Confidentialité dès la conception (35 s) · *faisabilité, pertinence*

**À l'écran** : « Loi organique 2004-63 · INPDP »
- ✅ **Comptes vérifiés** avant tout accès : justificatifs, contrôles automatiques, validation humaine sous 24 h
- 🔒 **Données chiffrées** au repos
- 🕶️ **Pseudonymisation** : aucun nom ni matricule n'est envoyé à l'IA externe
- 👁️ L'entreprise voit **qui a consulté son dossier** et **ce que reçoit l'IA**
- 📊 Ministre : statistiques anonymes, groupes de moins de 5 dossiers masqués
- 🧪 **8 tests de sécurité automatiques**, tous au vert

**Visuel** : `16_entreprise_confidentialite` (le bloc « Ce que voit l'IA » avec les jetons en surbrillance).

**Notes de l'orateur**
> « Ce sont des données couvertes par le secret fiscal. Chaque compte est vérifié avant d'ouvrir. Tout ce que l'entreprise saisit est chiffré. Avant chaque appel à l'IA, son nom et son matricule sont remplacés par des jetons : l'entreprise peut le vérifier elle-même, ici. Elle voit aussi chaque consultation de son dossier. »

---

## Slide 10 · Démonstration en direct (3 min) · *faisabilité, clarté*

**À l'écran** : « Démo » + le parcours en 5 étapes. Basculer ensuite sur l'application.

**Déroulé** (préparer les onglets à l'avance, comptes déjà connectés)
1. **(30 s) Entreprise, sur téléphone** : photographier la notification → analyse → 2 vices détectés (vérification de 7,9 mois au lieu de 6, art. 40 ; un chef non motivé, art. 43) → basculer en **العربية** → 🔊 écouter.
2. **(20 s) Confidentialité** : « Ce que voit l'IA » → nom et matricule remplacés par des jetons.
3. **(40 s) Messagerie** : l'entreprise écrit et joint ses factures → le message **arrive en direct** chez l'agent → « Pièces manquantes » → l'agent répond → ✓✓ côté entreprise.
4. **(50 s) Agent puis chef de centre** : dossier El Amen, score 47/100, facteurs SHAP, avis IA → conciliation **102 721 DT maintenant contre 84 721 DT espérés au tribunal** → validée par l'agent → **soumise au chef de centre**, qui la valide.
5. **(40 s) Ministre** : pilotage national en temps réel, filtre Sfax / Sousse / Tunis → groupes masqués → tentative d'ouvrir un dossier nominatif : refusée.

**Plan B** (Wi-Fi ou IA indisponible) : les captures de `docs/screenshots/v2/`, dans le même ordre, ou la vidéo de démonstration enregistrée la veille.

---

## Slide 11 · Résultats mesurés (30 s) · *faisabilité, impact*

**À l'écran**

| Indicateur | Résultat |
|---|---|
| AUC « chef maintenu devant le juge » | **0,84** |
| AUC « dossier recouvré à plus de 50 % » | **0,82** |
| Recouvré en traitant 20 % du stock : tri JISER vs ancienneté | **107,3 MDT vs 28,5 MDT (+276 %)** |
| Simulation calibrée vs jugements officiels 2020 | 51,9 / 33,6 / 14,5 % vs 51,5 / 33,9 / 14,5 % |
| Lecture d'une photo de notification | 9 champs sur 9, ~6 s |
| Tests de sécurité | 8/8 |

Mention en petit : « Mesuré sur 625 dossiers de test simulés, calibrés sur les statistiques officielles ; à réentraîner sur l'historique réel de la DGI. »

**Notes de l'orateur**
> « Nos données de dossiers sont simulées, parce que les vrais dossiers sont couverts par le secret fiscal, mais elles sont calibrées sur les jugements officiels de 2020. Sur 625 dossiers jamais vus, le modèle distingue bien un redressement solide d'un redressement fragile, et en traitant d'abord les dossiers que JISER recommande, on récupère presque 4 fois plus qu'en les traitant par ancienneté. »

---

## Slide 12 · Impact attendu (30 s) · *impact*

**À l'écran** : 3 colonnes
- **Pour l'État** : plus de recettes recouvrées plus tôt, moins d'annulations grâce au contrôle qualité, un stock qui cesse de grossir.
- **Pour les entreprises** : comprendre ses droits, répondre dans les délais, dialoguer sans intermédiaire, **dans sa langue**.
- **Pour la justice fiscale** : moins de dossiers au tribunal, des décisions tracées et expliquées.

Encadré « Simulateur d'impact » (capture du simulateur) : avec 20 % de dossiers réglés en conciliation et 50 % de dossiers traités en plus, **le stock grossit 40 % moins vite** (hypothèses réglables, pas une prévision).

**Notes de l'orateur**
> « Le simulateur, construit sur les flux officiels de 2020, montre l'effet des leviers. Avec des hypothèses prudentes, le stock grossit déjà 40 % moins vite. Ce ne sont pas des promesses : ce sont des hypothèses que la DGI pourra ajuster avec ses propres chiffres. »

---

## Slide 13 · Du prototype au déploiement national (30 s) · *faisabilité*

**À l'écran** : frise
1. **Mois 0-3 · Pilote** au CRCI Sfax 1 : historique réel anonymisé, réentraînement, mesure du gain réel (délai de clôture, taux de conciliation, taux d'annulation).
2. **Mois 3-9 · Industrialisation** : cloud souverain en Tunisie, LLM et OCR hébergés localement, SSO de l'État, connexion au registre national des entreprises et au SI de la DGI, déclaration INPDP.
3. **Mois 9-18 · Déploiement** dans les 27 centres, veille élargie (JORT, notes communes), ouverture aux conseillers fiscaux.

Petit schéma de l'architecture cible (README, section « Architecture cible »).

**Notes de l'orateur**
> « Le prototype fonctionne aujourd'hui, et son architecture est prête à migrer vers un hébergement souverain : même API, modèles de langage interchangeables, et les données ne quitteront pas la Tunisie. Nous proposons un pilote de trois mois dans un centre régional. »

---

## Slide 14 · L'équipe et notre demande (20 s) · *clarté*

**À l'écran**
- Photos, noms et rôle de chacun des 4 membres de l'équipe (quatre data scientists : [à compléter])
- **Notre demande** : un pilote avec un centre régional, l'accès à un historique anonymisé, un référent juridique à la DGI
- Clôture : logo · « JISER · جسر · le pont qui manquait » · QR code vers `github.com/EyaAzzabi/Jiser`

**Notes de l'orateur**
> « Nous sommes quatre data scientists, et nous avons construit une plateforme qui fonctionne déjà. Ce que nous demandons : un centre pilote, des données anonymisées et un juriste référent. JISER, le pont qui manquait entre le contribuable et l'administration. Merci. »

---

## Annexe · Réponses préparées aux questions du jury

| Question probable | Réponse courte |
|---|---|
| Vos données sont fausses ? | Les dossiers réels sont couverts par le secret fiscal. Nos dossiers simulés sont calibrés sur les jugements officiels 2020, et les chiffres affichés du ministère sont réels. En pilote : réentraînement sur l'historique de la DGI. |
| Vous envoyez des données fiscales à OpenAI ? | Non : nom, matricule et coordonnées sont remplacés par des jetons avant l'envoi, et l'entreprise peut le vérifier. Seule exception : la photo, signalée dans l'interface (le PDF reste l'option la plus confidentielle). En production : LLM et OCR hébergés en Tunisie. |
| Qui voit les données d'une entreprise ? | L'agent de son centre en charge du dossier et son chef de centre. Pas le ministre (statistiques anonymes), pas l'administrateur. L'entreprise voit chaque consultation. |
| Comment savez-vous que c'est bien le gérant, ou un agent ? | Justificatifs, contrôles automatiques (dont la concordance avec l'extrait RNE) et validation humaine ; un agent est validé par son chef de centre. En production : API du RNE et SSO de l'État. |
| Et quand la loi change ? | Veille hebdomadaire automatique, validation humaine, versions archivées, embeddings recalculés. Première exécution : 7 écarts détectés dans le Code de la TVA. |
| Et si l'IA se trompe ? | Elle ne décide rien. Les scores sont explicables, le LLM ne cite que les articles retrouvés, chaque recommandation et décision est tracée. |
| Pourquoi l'arabe standard ? | C'est la langue officielle des textes et de l'administration ; la terminologie fiscale officielle est respectée, avec lecture vocale. |
| Combien ça coûte ? | Un modèle d'IA léger (gpt-5.4-mini) avec un cache, Gemini gratuit en secours, et une stack open source. En production : l'infrastructure de l'État et des modèles ouverts hébergés localement. [À CHIFFRER avant la finale : coût réel d'une analyse, à lire sur le tableau de bord OpenAI.] |
| Qu'est-ce qui est vraiment nouveau ? | Le parcours complet des deux côtés, la hiérarchie et la confidentialité intégrées, la conciliation chiffrée, la veille juridique automatique. |
