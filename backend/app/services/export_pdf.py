"""PDF exports to download or share: the taxpayer's analysis report and the administration's file sheet."""
from __future__ import annotations

import io
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from xml.sax.saxutils import escape

from ..schemas import AnalyseNotification

LOGO = Path(__file__).resolve().parents[3] / "frontend" / "public" / "logo-icon.png"
NAVY, GOLD, BODY, RED, GREEN = (colors.HexColor(c) for c in ("#0b2f5b", "#9c7a1f", "#27324a", "#c0263d", "#0f7a4f"))

H1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=NAVY)
SUB = ParagraphStyle("sub", fontName="Helvetica", fontSize=9, leading=12, textColor=GOLD)
H2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=NAVY, spaceBefore=8, spaceAfter=3)
H3 = ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=BODY, spaceBefore=5, spaceAfter=1)
P = ParagraphStyle("p", fontName="Helvetica", fontSize=9, leading=12.5, textColor=BODY, alignment=TA_JUSTIFY, spaceAfter=2)
LI = ParagraphStyle("li", parent=P, leftIndent=10, bulletIndent=2)
SMALL = ParagraphStyle("small", parent=P, fontSize=7.5, leading=10, textColor=colors.HexColor("#6a7690"))
MONO = ParagraphStyle("mono", fontName="Courier", fontSize=8, leading=10.5, textColor=BODY)


def _t(s: object) -> str:
    return escape(str(s))


def _dt(x: float) -> str:
    return f"{round(x):,}".replace(",", " ") + " DT"


def _header(title: str, subtitle: str) -> list:
    head = Table([[Image(str(LOGO), width=15 * mm, height=15 * mm),
                   [Paragraph(_t(title), H1), Paragraph(_t(subtitle), SUB)]]], colWidths=[18 * mm, None])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    return [head, Spacer(1, 6)]


def _kv(rows: list[list[str]], widths=(60 * mm, None)) -> Table:
    t = Table([[Paragraph(f"<b>{_t(a)}</b>", P), Paragraph(_t(b), P)] for a, b in rows], colWidths=list(widths))
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dfe5ee")),
                           ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f5f7fa")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return t


def _build(story: list, title: str) -> bytes:
    buf = io.BytesIO()
    story += [Spacer(1, 8), Paragraph(
        f"Document généré par JISER le {date.today():%d/%m/%Y}. Analyse assistée par intelligence artificielle : à relire par un "
        "professionnel avant toute décision. Sources : Code des droits et procédures fiscaux, Code de la TVA, Code de l'IRPP et de l'IS.", SMALL)]
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=17 * mm, rightMargin=17 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                      title=title, author="JISER").build(story)
    return buf.getvalue()


def rapport_analyse(a: AnalyseNotification, lettre: str | None = None) -> bytes:
    n = a.notification
    story = _header(f"Analyse de la notification {n.reference}", f"{n.entreprise.nom} · {n.centre}")
    story.append(_kv([
        ["Montant réclamé", _dt(a.montant_total)],
        ["Montant contestable estimé", _dt(a.montant_contestable)],
        ["Date limite de réponse", f"{a.date_limite_reponse:%d/%m/%Y} (article 44 du CDPF)"],
        ["Vérification", f"{n.type_verification} · exercices {', '.join(map(str, n.exercices_verifies))}"],
    ]))
    story += [Paragraph("Résumé", H2), Paragraph(_t(a.resume), P), Paragraph("Contrôle de la procédure", H2)]
    for c in a.procedure:
        color = {"ok": GREEN, "vice": RED}.get(c.statut, GOLD)
        label = {"ok": "Conforme", "vice": "Vice", "a_verifier": "À vérifier"}[c.statut]
        story.append(Paragraph(f'<font color="{color.hexval()}"><b>{label}</b></font> — {_t(c.label)} '
                               f'({_t(c.article.replace("cdpf-art-", "art. "))} CDPF) : {_t(c.detail)}', LI, bulletText="•"))
    story.append(Paragraph("Chefs de redressement", H2))
    for ca in a.chefs:
        c = ca.chef
        story.append(Paragraph(f"{_t(c.id)} · {_t(c.libelle)} — {_dt(c.montant_principal + c.penalites)} "
                               f"({_t(ca.contestabilite)})", H3))
        story.append(Paragraph(f"<b>En clair :</b> {_t(ca.explication)}", P))
        for arg in ca.arguments:
            story.append(Paragraph(_t(arg), LI, bulletText="–"))
        story.append(Paragraph("<b>Pièces à rassembler :</b> " + _t("; ".join(ca.pieces_a_fournir)), P))
        if ca.articles:
            story.append(Paragraph("<b>Articles :</b> " + _t(", ".join(
                f"art. {r.article} ({r.code.upper()})" for r in ca.articles)), P))
    if lettre:
        story += [Paragraph("Brouillon de réponse", H2)] + [Paragraph(_t(line) or "&nbsp;", MONO) for line in lettre.splitlines()]
    return _build(story, f"JISER · Analyse {n.reference}")


def fiche_dossier(detail: dict, avis: dict | None = None) -> bytes:
    n = detail["dossier"]["notification"]
    s = detail["score"]
    c = detail["conciliation"]
    story = _header(f"Fiche dossier {n['reference']}", f"{n['entreprise']['nom']} · {n['centre']} · {detail['dossier']['etape']}")
    story.append(_kv([
        ["Montant notifié", _dt(c["montant_notifie"])],
        ["Score de solidité", f"{s['score_solidite']}/100 · probabilité de maintien {round(s['proba_maintien'] * 100)} %"],
        ["Montant recouvrable estimé", _dt(s["montant_recouvrable_estime"])],
        ["Proposition de conciliation", f"{_dt(c['montant_propose'])} (espérance au contentieux : {_dt(c['montant_attendu_contentieux'])})"],
    ]))
    story.append(Paragraph("Facteurs du score (SHAP)", H2))
    for e in s["explications"]:
        story.append(Paragraph(f"{_t(e['facteur'])} : {e['impact']:+.2f}", LI, bulletText="•"))
    vices = [p for p in detail["procedure"] if p["statut"] == "vice"]
    if vices:
        story.append(Paragraph("Vices de procédure", H2))
        for p in vices:
            story.append(Paragraph(_t(p["detail"]), LI, bulletText="•"))
    story.append(Paragraph("Proposition de conciliation par chef", H2))
    rows = [["Chef", "Notifié", "P(maintenu)", "Recommandation", "Proposé"]] + [
        [f"{i['chef_id']} · {i['libelle']}", _dt(i["montant"]), f"{round(i['p_maintenu'] * 100)} %", i["action"], _dt(i["montant_propose"])]
        for i in c["items"]]
    t = Table([[Paragraph(_t(x), P) for x in r] for r in rows], colWidths=[70 * mm, 25 * mm, 22 * mm, 28 * mm, 25 * mm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dfe5ee")),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f1fb"))]))
    story.append(t)
    if avis:
        story += [Paragraph("Avis juridique de l'IA", H2), Paragraph(_t(avis["avis"]), P),
                  Paragraph("Projet de lettre de conciliation", H2)]
        story += [Paragraph(_t(line) or "&nbsp;", MONO) for line in avis["lettre_conciliation"].splitlines()]
    return _build(story, f"JISER · Dossier {n['reference']}")
