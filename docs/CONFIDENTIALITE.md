# Confidentialité des données : ce que JISER garantit

Les données saisies par les entreprises (notifications de redressement, montants, réponses, échanges, justificatifs d'identité) sont couvertes par le **secret fiscal** et par la **loi organique n° 2004-63 du 27 juillet 2004** relative à la protection des données à caractère personnel, contrôlée par l'**INPDP**. Ce texte est l'équivalent tunisien du RGPD européen : finalité déterminée, proportionnalité, sécurité, droits d'accès, de rectification et d'opposition.

JISER applique la **protection des données dès la conception** : chaque garantie ci-dessous est implémentée dans le code et vérifiée par des tests automatiques ([tests/test_securite_acces.py](../tests/test_securite_acces.py)).

## 1. Qui voit quoi

| Donnée | Entreprise | Chargé(e) du contentieux | Chef de centre | Ministre | Admin plateforme |
|---|---|---|---|---|---|
| Ses propres analyses et réponses | ✅ | ❌ | ❌ | ❌ | ❌ |
| Dossier nominatif de l'administration | — | son centre (affecté à lui en priorité) | son centre | ❌ | ❌ |
| Messages d'un dossier | les siens | si affecté (ou non affecté) dans son centre | son centre | ❌ | ❌ |
| Statistiques | — | son centre | son centre | **nationales, anonymes** | usage de la plateforme |
| Justificatifs d'identité | les siens | ❌ | ceux de ses agents | ❌ | ceux à valider |

- Le rôle est **relu en base à chaque requête** : il n'est jamais pris dans le navigateur.
- Un dossier hors périmètre répond « introuvable » : on ne peut même pas savoir qu'il existe.
- Le ministre ne voit que des agrégats. Tout groupe de **moins de 5 dossiers est masqué** (k-anonymat), pour qu'aucune entreprise ne soit reconnaissable.

## 2. Chiffrement au repos

Chiffrés (Fernet : AES-128-CBC + HMAC-SHA256) avant d'être écrits en base, dans [services/db.py](../backend/app/services/db.py) :
- résultats d'analyse des notifications ;
- brouillons de réponse ;
- messages et pièces jointes de la messagerie ;
- justificatifs d'identité (extrait RNE, CIN, décisions de nomination).

La clé (`JISER_DATA_KEY`) reste sur le serveur. Même un accès direct à la base (Supabase) ne donne que du texte illisible.

## 3. Pseudonymisation avant toute IA externe

Avant chaque appel à un modèle de langage (OpenAI, ou Gemini en secours), [services/securite.py](../backend/app/services/securite.py) remplace :
- la raison sociale → `[ENTREPRISE_1]`
- le matricule fiscal → `[MATRICULE_1]`
- les noms de personnes → `[PERSONNE_1]`
- e-mails, téléphones, RIB, numéros de CIN → `[EMAIL_1]`, `[TELEPHONE_1]`…

L'IA répond avec ces jetons ; JISER remet les vraies valeurs **uniquement sur l'écran de l'utilisateur**. Le cache disque des réponses de l'IA ne contient que du texte pseudonymisé. La synthèse vocale reçoit des mots neutres (« votre entreprise »). Les montants et les articles de loi restent visibles : l'IA en a besoin pour expliquer.

L'entreprise voit en direct, dans « Confidentialité », **ce que l'IA reçoit** pour ses propres dossiers.

Les images de justificatifs ne sont **jamais envoyées à une IA externe** : seuls les PDF sont lus, localement.

**Exception assumée : la photo d'une notification.** Une image ne peut pas être pseudonymisée comme un texte. Quand l'entreprise photographie sa notification, la photo est lue par le modèle de vision, dans le cadre de son consentement à l'IA générative. L'interface le dit clairement sous les boutons photo, et recommande de déposer le PDF pour une confidentialité maximale. Tout ce qui suit la lecture (explications, assistant, rédaction) repasse par la pseudonymisation. En production, un OCR hébergé localement supprimerait cette exception.

## 4. Consentement et droits de la personne

| Droit (loi 2004-63) | Dans JISER |
|---|---|
| Consentement explicite | À l'inscription : conditions d'utilisation, traitement des données, IA générative (séparément) |
| Retrait du consentement | Interrupteur « IA générative » : JISER fonctionne alors avec ses règles et son modèle interne uniquement |
| Droit d'accès | Bouton « Exporter toutes mes données » (fichier JSON complet, déchiffré) |
| Transparence | Page « Qui a consulté mes dossiers » : rôle, centre, action, date de chaque consultation |
| Droit à l'effacement | « Supprimer mon compte » : analyses, réponses, messages, justificatifs et favoris effacés |
| Information | Registre des traitements affiché dans l'application (finalité, base légale, durée, destinataires) |

## 5. Contrôle d'accès et traçabilité

- Connexion par code à usage unique envoyé par e-mail (haché, 5 minutes, 5 essais).
- **Vérification de chaque compte avant accès** : pré-contrôles automatiques puis validation humaine sous 24 h. Les agents sont validés par **le chef de leur centre**.
- Journal d'audit de chaque recommandation de l'IA, de chaque décision humaine et de chaque consultation de dossier.
- Supabase avec Row Level Security activée et aucune politique publique : seule l'API accède aux données.
- E-mails de notification : ils ne contiennent **jamais** le contenu d'un message ni d'un dossier.

## 6. Ce qu'il reste à faire pour la production

- Déclaration du traitement à l'INPDP et analyse d'impact.
- Hébergement en Tunisie et modèle de langage hébergé localement (la passerelle `llm.py` le permet déjà).
- Rotation de la clé de chiffrement et stockage dans un coffre-fort de secrets (HSM).
- Purge automatique selon les durées du registre.
