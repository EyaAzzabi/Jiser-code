"""Build the 2-page synthesis note (docs/JISER_note_de_synthese.pdf) required by the hackathon."""
from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "JISER_note_de_synthese.pdf"
NAVY, GOLD, BODY = colors.HexColor("#0b2f5b"), colors.HexColor("#9c7a1f"), colors.HexColor("#27324a")

m = json.loads((ROOT / "models" / "metrics.json").read_text(encoding="utf-8"))
off = json.loads((ROOT / "data" / "real" / "indicateurs_officiels.json").read_text(encoding="utf-8"))
ct = off["contentieux"]
nb = lambda n: f"{n:,}".replace(",", " ")

h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=17, leading=20, textColor=NAVY)
sub = ParagraphStyle("sub", fontName="Helvetica", fontSize=9.5, leading=12, textColor=GOLD)
h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=NAVY, spaceBefore=5, spaceAfter=2)
p = ParagraphStyle("p", fontName="Helvetica", fontSize=8.6, leading=11.2, textColor=BODY, alignment=TA_JUSTIFY, spaceAfter=2)
li = ParagraphStyle("li", parent=p, leftIndent=9, bulletIndent=1, spaceAfter=1)
small = ParagraphStyle("small", parent=p, fontSize=7.4, leading=9.4)


def bullets(items):
    return [Paragraph(t, li, bulletText="•") for t in items]


story = []
header = Table([[Image(str(ROOT / "frontend" / "public" / "logo-icon.png"), width=17 * mm, height=17 * mm),
                 [Paragraph("JISER — Le pont entre le contribuable et l'administration fiscale", h1),
                  Paragraph("Note de synthèse · Hackathon national IA &amp; Finances publiques 2026 · Défi principal T3 "
                            "(contrôles et analyses a posteriori de la conformité), avec T9, T14 et T20", sub)]]],
               colWidths=[20 * mm, None])
header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
story += [header, Spacer(1, 4)]

story.append(Paragraph("1. Le défi choisi", h2))
story.append(Paragraph(
    "Quand l'administration notifie un redressement, l'entreprise dispose de 45 jours pour répondre (art. 43 et 44 du CDPF, "
    "édition officielle 2024), faute de quoi la taxation est établie d'office. La notification est technique : la PME comprend mal "
    "ce qui lui est reproché et répond tard ou mal. Côté administration, le stock explose : selon le ministère des Finances "
    f"(rapport annuel de performance 2020), <b>{nb(ct['affaires_enrolees']['2020'])} affaires de contentieux ont été enrôlées en 2020 "
    f"pour seulement {nb(ct['affaires_jugees']['2020'])} jugées</b>, soit près de 3 900 dossiers de plus chaque année ; "
    "14,5 % des affaires jugées se terminent par une annulation, souvent pour vice de procédure ou défaut de motivation. "
    "Chaque dossier bloqué est une recette non recouvrée. JISER traite ce contentieux des deux côtés à la fois.", p))

story.append(Paragraph("2. La solution", h2))
story += bullets([
    "<b>Espace entreprise</b> : dépôt de la notification (PDF, fichier ou <b>photo prise directement avec le téléphone</b>), "
    "explication chef par chef en français ou en tounsi, <b>lecture à voix haute</b> (français, anglais, tounsi), contestabilité, "
    "vices de procédure, articles cités, pièces à réunir, date limite avec <b>rappels e-mail à J-15, J-7, J-3 et J-1</b>, "
    "assistant fiscal en streaming, brouillon de réponse (art. 44), favoris, export PDF et partage.",
    "<b>Espace administration</b> (chef du contentieux) : tableau de bord avec synthèse IA du stock, <b>chiffres officiels du "
    "ministère des Finances</b> et <b>simulateur d'impact</b> (conciliation, contrôle qualité, productivité : effet sur le stock "
    "national), stock trié par montant recouvrable, score de solidité expliqué (SHAP), avis juridique et lettre de conciliation, "
    "contrôle qualité d'une notification avant envoi, copilote juridique ; chaque décision de l'agent est inscrite au journal.",
    "<b>Espace administrateur privé</b> (lien et e-mails autorisés uniquement) : pouls de la plateforme (activité, profils, part "
    "de l'IA, taux d'accord humain avec l'IA), utilisateurs, journal d'audit, base juridique, état des services.",
])

story.append(Paragraph("3. Approche technique", h2))
story.append(Paragraph(
    "Trois couches complémentaires. <b>Règles</b> : 8 contrôles déterministes du CDPF (avis préalable et délai de 15 jours, "
    "art. 39 ; durée maximale de 6 mois ou 1 an, art. 40 ; motivation, délai de 45 jours et pénalités, art. 43-44 ; droit de "
    "reprise de 4 ans, art. 19-20). <b>Machine learning</b> : un modèle XGBoost prédit pour chaque chef l'issue « maintenu / réduit / "
    "annulé » à partir de 26 variables (type de chef, montant, qualité de la motivation, base légale, vices, justificatifs, "
    "réponse du contribuable…) ; SHAP explique chaque score ; le tri du stock combine montant recouvrable estimé et ancienneté. "
    "<b>IA générative</b> : OpenAI gpt-5.4-mini (Gemini Flash en secours automatique) lit les photos, reformule en français ou en "
    "tounsi, répond aux questions par recherche augmentée (BM25 sur 305 articles), rédige réponses, avis et conciliations. "
    "Garde-fous : sorties structurées validées (Pydantic), le modèle ne cite que les articles fournis, repli sur les règles et le "
    "modèle ML si l'IA ne répond pas.", p))
story.append(Paragraph(
    "Architecture : interface React/TypeScript, API FastAPI (Python), base Supabase (PostgreSQL, sécurité par ligne activée), "
    "automatisation n8n (e-mails de code, bienvenue, rappels de délais). Sécurité : code à usage unique par e-mail (6 chiffres, "
    "5 minutes, 5 essais, stocké haché), sessions à jeton haché, contrôle des rôles sur chaque route, journal de traçabilité.", p))

story.append(Paragraph("4. Données et modèles utilisés", h2))
story += bullets([
    "<b>Textes de loi officiels</b> : CDPF, édition officielle 2024 (jibaya.tn, 154 articles importés du PDF officiel), Code de "
    "l'IRPP et de l'IS (114) et Code de la TVA (27) (Jurisite Tunisie), découpés article par article.",
    "<b>Données publiques réelles</b> : rapport annuel de performance 2020 de la mission « Finances » (gbo.tn) : affaires "
    "enrôlées et jugées, issues des jugements, durée des vérifications, taux de confirmation ; loi de finances 2026 (recettes "
    "fiscales). Affichées telles quelles dans le tableau de bord.",
    "<b>Données synthétiques calibrées</b> : les dossiers individuels sont couverts par le secret fiscal (loi organique "
    "2004-63). 2 822 dossiers fictifs (2 500 clôturés, 322 en cours) reproduisent la répartition officielle des jugements 2020 "
    "(51,5 % confirmés, 33,9 % révisés ou conciliés, 14,5 % annulés ; simulation : 51,9 / 33,6 / 14,5 %). Taux de recouvrement "
    "simulé : 70 % contre 71,8 % officiel. Aucune donnée réelle de contribuable.",
    "<b>Modèles et services tiers</b> : OpenAI gpt-5.4-mini, Google Gemini (Flash), XGBoost, SHAP, scikit-learn, rank-bm25, "
    "pypdf, ReportLab, FastAPI, React, Tailwind CSS, Recharts, Supabase, n8n. Le code a été écrit pendant le hackathon avec "
    "l'aide de l'assistant de programmation Claude (Anthropic).",
])

story.append(Paragraph("5. Résultats obtenus", h2))
res = Table([
    ["Indicateur (625 dossiers de test jamais vus)", "Résultat"],
    ["AUC « chef maintenu devant le juge »", f"{m['auc_chef_maintenu']:.2f}".replace(".", ",")],
    ["AUC « dossier recouvré à plus de 50 % »", f"{m['auc_dossier_recouvre_50pct']:.2f}".replace(".", ",")],
    ["Montant recouvré en traitant 20 % du stock : tri JISER vs ancienneté",
     f"{m['triage']['recouvre_jiser'] / 1e6:.1f} MDT vs {m['triage']['recouvre_fifo'] / 1e6:.1f} MDT (+{m['triage']['gain_vs_fifo_pct']:.0f} %)".replace(".", ",")],
    ["Même comparaison vs « plus gros montants d'abord »", f"+{m['triage']['gain_vs_plus_gros_pct']:.1f} %".replace(".", ",")],
], colWidths=[118 * mm, 52 * mm])
res.setStyle(TableStyle([
    ("FONT", (0, 0), (-1, -1), "Helvetica", 8.4), ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.4),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), NAVY),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f5f7fa"), colors.white]),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dfe5ee")), ("TOPPADDING", (0, 0), (-1, -1), 2.5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
story += [res, Spacer(1, 3)]
story.append(Paragraph(
    "Prototype fonctionnel de bout en bout, testé dans un navigateur : inscription avec code reçu par e-mail, analyse d'une "
    "notification de 180 000 DT (2 vices détectés : durée de vérification, art. 40 ; chef non motivé, art. 43), explications en "
    "tounsi et à voix haute, brouillon de réponse, avis juridique et proposition de conciliation (102 721 DT encaissables tout de "
    "suite contre une espérance de 84 721 DT au contentieux, dans plusieurs années). Utilisable sur téléphone. Ces performances "
    "sont mesurées sur des données simulées calibrées : elles valident la méthode, pas un gain réel. Face au tri par montant, le "
    "gain est faible ; l'apport principal de JISER est l'explication des scores, le contrôle qualité et la conciliation.", p))

story.append(Paragraph("6. Ce que nous avons construit", h2))
built = Table([
    ["3 espaces", "Entreprise, administration, admin plateforme privé ; utilisable sur ordinateur et sur téléphone"],
    ["3 types d'IA", "8 règles du CDPF · XGBoost + SHAP (26 variables) · LLM + RAG sur 305 articles, avec secours automatique"],
    ["40 routes d'API", "Analyse, rédaction, assistant en streaming, voix, export PDF, favoris, notifications, conciliation, audit"],
    ["Données réelles", "CDPF officiel 2024 · statistiques du ministère des Finances (RAP 2020) · loi de finances 2026"],
    ["Automatisations", "E-mails n8n : code de connexion, bienvenue, échéance enregistrée, rappels J-15 / J-7 / J-3 / J-1"],
    ["Langues", "Français, tounsi (écrit et oral), anglais pour la lecture à voix haute"],
], colWidths=[30 * mm, 148 * mm])
built.setStyle(TableStyle([
    ("FONT", (0, 0), (-1, -1), "Helvetica", 8.2), ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 8.2),
    ("TEXTCOLOR", (0, 0), (0, -1), NAVY), ("TEXTCOLOR", (1, 0), (1, -1), BODY),
    ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#f5f7fa"), colors.white]),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dfe5ee")), ("TOPPADDING", (0, 0), (-1, -1), 2.5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
story += [built, Spacer(1, 5)]

cap = ParagraphStyle("cap", parent=small, alignment=1, textColor=GOLD)
shots = ROOT / "docs" / "screenshots" / "note"
w = 55 * mm
row1 = [Image(str(shots / "10_administration_tableau_de_bord.jpg"), width=w, height=w * 900 / 1440),
        Image(str(shots / "12_administration_dossier_avis_ia.jpg"), width=w, height=w * 940 / 1190),
        Image(str(shots / "07_entreprise_analyse_derja_brouillon.jpg"), width=w, height=w * 940 / 1190)]
caps1 = [Paragraph("Chiffres officiels et simulateur d'impact", cap), Paragraph("Score SHAP et avis juridique de l'IA", cap),
         Paragraph("Notification expliquée en tounsi", cap)]
gal = Table([row1, caps1], colWidths=[59 * mm] * 3)
gal.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, 0), "BOTTOM"),
                         ("LEFTPADDING", (0, 0), (-1, -1), 1), ("RIGHTPADDING", (0, 0), (-1, -1), 1)]))
story += [gal, Spacer(1, 2)]

story.append(Paragraph("7. Limites identifiées", h2))
story += bullets([
    "Modèle entraîné sur données synthétiques calibrées ; chiffres officiels détaillés les plus récents : 2020 ; jurisprudence "
    "non intégrée ; base juridique à synchroniser avec chaque loi de finances.",
    "Les comptes des agents devraient être validés par un administrateur ; les rappels automatiques supposent une API en ligne.",
    "L'IA générative peut se tromper : elle ne décide rien, cite ses sources et reste soumise à relecture humaine.",
])

story.append(Paragraph("8. Recommandations pour une mise en production", h2))
story += bullets([
    "Pilote dans un centre régional de contrôle des impôts (par exemple Sfax) sur l'historique réel anonymisé, puis réentraînement "
    "et mesure du gain réel (délai de clôture, taux de conciliation, taux d'annulation).",
    "Intégration au système d'information de la DGI ; base juridique alimentée par les textes officiels (JORT, notes communes).",
    "Hébergement en Tunisie, modèle de langage hébergé localement ou sous contrat, avis de l'INPDP (loi organique 2004-63).",
    "Dépôt en ligne de la réponse du contribuable, interface en arabe, validation des comptes agents par l'administrateur.",
])
story.append(Spacer(1, 3))
story.append(Paragraph("Code source : github.com/EyaAzzabi/Jiser · L'IA recommande et explique, un humain décide toujours.", small))

doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=13 * mm, bottomMargin=12 * mm,
                        title="JISER · Note de synthèse", author="Équipe JISER")
doc.build(story)
print("written", OUT)
