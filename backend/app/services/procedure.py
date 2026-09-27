"""CDPF procedure checklist: deterministic, explainable rules (no ML).

Each rule cites its article so the taxpayer, the auditor and the judge can check it.
Labels and details exist in French and in Modern Standard Arabic (langue="ar").
"""
from __future__ import annotations

from ..domain import (DELAI_AVIS_MIN_JOURS, DROIT_REPRISE_ANS, DUREE_MAX_AUTRES_MOIS,
                      DUREE_MAX_COMPTA_MOIS, PROCEDURE_RULES)
from ..schemas import Notification, ProcedureCheck

_RULES = {r["code"]: r for r in PROCEDURE_RULES}


def check_procedure(n: Notification, langue: str = "fr") -> list[ProcedureCheck]:
    ar = langue == "ar"

    def t(fr: str, arabe: str) -> str:
        return arabe if ar else fr

    def check(code: str, statut: str, detail: str) -> ProcedureCheck:
        r = _RULES[code]
        return ProcedureCheck(code=code, label=r["label_ar"] if ar else r["label"], article=r["article"], statut=statut, detail=detail)

    out: list[ProcedureCheck] = []
    if n.type_verification == "approfondie":
        if n.date_avis is None:
            out.append(check("AVIS_PREALABLE", "a_verifier", t(
                "La date de l'avis préalable n'apparaît pas dans la notification : demander la copie de l'avis.",
                "لا يظهر تاريخ الإعلام المسبق في الإعلام بالنتائج: اطلبوا نسخة منه.")))
        else:
            out.append(check("AVIS_PREALABLE", "ok", t(f"Avis notifié le {n.date_avis:%d/%m/%Y}.",
                                                       f"تم تبليغ الإعلام بتاريخ {n.date_avis:%d/%m/%Y}.")))
        if n.date_avis and n.date_debut_verification:
            gap = (n.date_debut_verification - n.date_avis).days
            out.append(check("DELAI_AVIS_15J", "ok" if gap >= DELAI_AVIS_MIN_JOURS else "vice", t(
                f"{gap} jours entre l'avis et le début de la vérification (minimum légal : {DELAI_AVIS_MIN_JOURS} jours).",
                f"{gap} يومًا بين الإعلام وانطلاق المراجعة (الحد الأدنى القانوني: {DELAI_AVIS_MIN_JOURS} يومًا).")))
        out.append(check("MENTION_ASSISTANCE", "ok" if n.mention_assistance else "vice",
                         t("Le droit de se faire assister est mentionné.", "تم التنصيص على حق الاستعانة بشخص.")
                         if n.mention_assistance else
                         t("Aucune mention du droit de se faire assister par une personne de son choix.",
                           "لم يتم التنصيص على حق الاستعانة بشخص يختاره المطالب بالأداء.")))
        if n.date_debut_verification:
            max_m = DUREE_MAX_COMPTA_MOIS if n.comptabilite_conforme else DUREE_MAX_AUTRES_MOIS
            months = (n.date_notification - n.date_debut_verification).days / 30.44
            out.append(check("DUREE_MAX", "ok" if months <= max_m else "vice", t(
                f"Durée de la vérification : {months:.1f} mois, du {n.date_debut_verification:%d/%m/%Y} "
                f"au {n.date_notification:%d/%m/%Y} (maximum : {max_m} mois "
                f"{'avec une comptabilité conforme' if n.comptabilite_conforme else 'sans comptabilité admise'}).",
                f"مدة المراجعة: {months:.1f} شهرًا، من {n.date_debut_verification:%d/%m/%Y} إلى {n.date_notification:%d/%m/%Y} "
                f"(الحد الأقصى: {max_m} أشهر {'مع محاسبة مطابقة' if n.comptabilite_conforme else 'دون محاسبة مقبولة'}).")))
    motives = [c for c in n.chefs if c.motivation_qualite == "absente"]
    out.append(check("CHEFS_MOTIVES", "ok" if not motives else "vice",
                     t("Tous les chefs de redressement sont motivés.", "جميع عناصر التعديل معلّلة.") if not motives else
                     t(f"{len(motives)} chef(s) sans motivation : " + ", ".join(c.id for c in motives) + ".",
                       f"{len(motives)} من عناصر التعديل دون تعليل: " + "، ".join(c.id for c in motives) + ".")))
    out.append(check("MENTION_DELAI_30J", "ok" if n.mention_delai_30j else "vice",
                     t("Le délai de réponse de 45 jours est indiqué.", "تم بيان أجل الرد المحدد بـ 45 يومًا.")
                     if n.mention_delai_30j else
                     t("La notification n'invite pas à répondre dans le délai légal de 45 jours (art. 43 et 44, édition 2024).",
                       "لا يتضمن الإعلام الدعوة إلى الرد في الأجل القانوني المحدد بـ 45 يومًا (الفصلان 43 و44).")))
    out.append(check("PENALITES_INDIQUEES", "ok" if n.penalites_indiquees else "vice",
                     t("Les pénalités sont chiffrées.", "تم بيان مبلغ الخطايا.") if n.penalites_indiquees else
                     t("Les pénalités ne sont pas chiffrées dans la notification.", "لم يتم بيان مبلغ الخطايا في الإعلام.")))
    late = [y for y in n.exercices_verifies if n.date_notification.year > y + DROIT_REPRISE_ANS]
    out.append(check("DROIT_REPRISE", "ok" if not late else "vice",
                     t("Tous les exercices sont dans le délai de reprise de 4 ans.", "جميع السنوات المراجعة داخلة في أجل التقادم (4 سنوات).")
                     if not late else
                     t(f"Exercice(s) {', '.join(map(str, late))} hors délai de reprise de 4 ans (sauf impôt non déclaré : 10 ans, art. 20).",
                       f"السنة أو السنوات {'، '.join(map(str, late))} خارج أجل التقادم المحدد بأربع سنوات (باستثناء الأداء غير المصرح به: 10 سنوات، الفصل 20).")))
    return out


def vice_codes(n: Notification) -> set[str]:
    # CHEFS_MOTIVES is a per-item weakness, handled by the item-level model, not a file-level defect
    return {c.code for c in check_procedure(n) if c.statut == "vice" and c.code != "CHEFS_MOTIVES"}
