"""Generate the three n8n workflows used by JISER (importable JSON files in n8n/).

1. jiser-otp.json        Webhook -> check secret -> send the OTP e-mail -> respond
2. jiser-bienvenue.json  Webhook -> check secret -> send the welcome e-mail (account activated) -> respond
3. jiser-rappels.json    Every day 08:00 -> GET /api/n8n/echeances -> reminder e-mail per reply due within 7 days

After import in n8n: set the SMTP credential on the "Envoyer" nodes, replace CHANGE_ME_SECRET with the
value of N8N_SHARED_SECRET from .env, set the API URL in the reminder workflow, then activate.
`--local you@gmail.com` (SMTP) or `--cloud` (n8n Cloud, Gmail node) bakes the real secret into n8n/local/ (git-ignored).
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "n8n"
SECRET = "CHANGE_ME_SECRET"
FROM = "JISER <no-reply@jiser.tn>"
API = "http://localhost:8000"

NAVY, GOLD = "#0b2f5b", "#c29a2e"


def page(title: str, body: str) -> str:
    """Plain, text-heavy layout: spam filters penalise image-like headers, big coloured blocks and short bodies."""
    return f"""<div style="font-family:Arial,Helvetica,sans-serif;color:#1e293b;font-size:15px;line-height:1.6;max-width:560px;margin:auto;padding:16px">
<p style="font-size:20px;font-weight:bold;color:{NAVY};margin:0 0 4px">JISER</p>
<p style="color:#64748b;font-size:13px;margin:0 0 20px">Plateforme d'accompagnement du contentieux fiscal</p>
<h2 style="color:{NAVY};font-size:18px;margin:0 0 12px">{title}</h2>{body}
<hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0 12px">
<p style="color:#64748b;font-size:12px;margin:0">Vous recevez ce message parce qu'une action a été effectuée avec votre adresse e-mail sur JISER.
Si ce n'est pas vous, ignorez simplement ce message. L'équipe JISER ne vous demandera jamais votre code.</p>
</div>"""


def button(link_expr: str, label: str) -> str:
    """Call-to-action shown only with a public URL: links to localhost are a strong spam signal."""
    a = (f"'<p><a href=\"' + {link_expr} + '\" style=\"background:{NAVY};color:#ffffff;padding:10px 18px;"
         f"border-radius:8px;text-decoration:none;font-weight:bold\">{label}</a></p>'")
    return "{{ (" + link_expr + " || '').includes('localhost') ? '' : " + a + " }}"


def node(name: str, ntype: str, version: float, params: dict, pos: tuple[int, int], creds: dict | None = None) -> dict:
    n = {"id": str(uuid.uuid4()), "name": name, "type": ntype, "typeVersion": version, "position": list(pos), "parameters": params}
    if creds:
        n["credentials"] = creds
    return n


def secret_check(name: str, pos) -> dict:
    return node(name, "n8n-nodes-base.if", 2, {
        "conditions": {
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
            "conditions": [{"id": str(uuid.uuid4()), "leftValue": "={{ $json.headers['x-jiser-secret'] }}",
                            "rightValue": SECRET, "operator": {"type": "string", "operation": "equals"}}],
            "combinator": "and"},
        "options": {}}, pos)


def respond(name: str, code: int, pos) -> dict:
    return node(name, "n8n-nodes-base.respondToWebhook", 1.1, {
        "respondWith": "json", "responseBody": json.dumps({"ok": code == 200}),
        "options": {"responseCode": code}}, pos)


USE_GMAIL = False   # --cloud: Gmail node with Google sign-in (no SMTP password needed)


def email(name: str, to: str, subject: str, html: str, pos) -> dict:
    if USE_GMAIL:
        return node(name, "n8n-nodes-base.gmail", 2.1, {
            "sendTo": to, "subject": subject, "emailType": "html", "message": html,
            "options": {"appendAttribution": False, "senderName": "JISER"}},
            pos, {"gmailOAuth2": {"id": "", "name": "Gmail JISER"}})
    return node(name, "n8n-nodes-base.emailSend", 2.1, {
        "fromEmail": FROM, "toEmail": to, "subject": subject, "emailFormat": "html", "html": html, "options": {}},
        pos, {"smtp": {"id": "", "name": "SMTP JISER"}})


def webhook_flow(wf_name: str, path: str, send: dict) -> dict:
    wh = node("Webhook", "n8n-nodes-base.webhook", 2, {"httpMethod": "POST", "path": path, "responseMode": "responseNode", "options": {}}, (0, 0))
    wh["webhookId"] = str(uuid.uuid4())
    chk = secret_check("Secret valide ?", (240, 0))
    ok = respond("Réponse OK", 200, (720, -100))
    ko = respond("Refusé", 401, (480, 120))
    send["position"] = [480, -100]
    return {
        "name": wf_name, "nodes": [wh, chk, send, ok, ko],
        "connections": {
            "Webhook": {"main": [[{"node": chk["name"], "type": "main", "index": 0}]]},
            chk["name"]: {"main": [[{"node": send["name"], "type": "main", "index": 0}], [{"node": ko["name"], "type": "main", "index": 0}]]},
            send["name"]: {"main": [[{"node": ok["name"], "type": "main", "index": 0}]]},
        },
        "settings": {"executionOrder": "v1"}, "active": False,
    }


def otp_workflow() -> dict:
    b = "$('Webhook').item.json.body"
    html = page("Votre code de connexion",
                "<p>Bonjour,</p>"
                "<p>Vous avez demandé à vous connecter à votre espace JISER. Saisissez le code ci-dessous dans la page de connexion :</p>"
                f"<p style=\"font-size:28px;letter-spacing:6px;font-weight:bold;color:{NAVY};margin:16px 0\">{{{{ {b}.code }}}}</p>"
                "<p>Ce code est valable {{ " + b + ".expire_minutes }} minutes et ne peut être utilisé qu'une seule fois.</p>"
                "<p>Cordialement,<br>L'équipe JISER</p>")
    send = email("Envoyer le code", "={{ " + b + ".email }}", "Votre code de connexion JISER", "=" + html, (0, 0))
    return webhook_flow("JISER · Code OTP par e-mail", "jiser-otp", send)


def welcome_workflow() -> dict:
    html = page("Bienvenue sur JISER, {{ $('Webhook').item.json.body.prenom }}",
                "<p>Votre espace <b>{{ $('Webhook').item.json.body.role_label }}</b> est activé. Votre identité a été vérifiée par code à usage unique.</p>"
                "<p><b>Vos prochaines étapes :</b></p>"
                "{{ ({"
                "entreprise: '<ol><li>Déposez votre notification de redressement</li><li>Lisez l\\'analyse chef par chef</li><li>Générez votre brouillon de réponse avant la date limite</li></ol>',"
                "conseil: '<ol><li>Analysez la notification de votre client</li><li>Vérifiez les vices de procédure</li><li>Complétez le brouillon de réponse</li></ol>',"
                "verificateur: '<ol><li>Déposez votre projet de notification</li><li>Corrigez les points de procédure signalés</li><li>Renforcez les chefs mal motivés</li></ol>',"
                "contentieux: '<ol><li>Consultez le stock trié par priorité</li><li>Ouvrez un dossier : score et explication</li><li>Validez les propositions de conciliation</li></ol>'"
                "})[$('Webhook').item.json.body.role] || '' }}"
                + button("$('Webhook').item.json.body.lien", "Accéder à mon espace") +
                "<p style=\"color:#64748b;font-size:13px\">L'IA de JISER recommande et explique ; la décision reste toujours humaine.</p>")
    send = email("Envoyer la bienvenue", "={{ $('Webhook').item.json.body.email }}",
                 "Votre espace JISER est activé", "=" + html, (0, 0))
    return webhook_flow("JISER · E-mail de bienvenue (activation)", "jiser-bienvenue", send)


def reminder_push_workflow() -> dict:
    """Deadline e-mail pushed by the JISER API (works with n8n Cloud: no call back to the API needed)."""
    b = "$('Webhook').item.json.body"
    html = page("{{ " + b + ".palier === 'enregistrement' ? 'Votre échéance est enregistrée' : 'Rappel : plus que ' + " + b + ".jours_restants + ' jour(s)' }}",
                "<p>Bonjour {{ " + b + ".prenom }},</p>"
                "<p>Notification <b>{{ " + b + ".reference }}</b> ({{ " + b + ".entreprise }}) : vous devez répondre par écrit "
                "<b>avant le {{ " + b + ".date_limite }}</b>, soit dans <b>{{ " + b + ".jours_restants }} jour(s)</b>.</p>"
                "<p>Passé ce délai, la taxation peut être établie d'office (articles 44 et 47 du CDPF). "
                "JISER vous a préparé l'analyse de chaque chef et un brouillon de réponse.</p>"
                + button(b + ".lien", "Préparer ma réponse") +
                "<p style=\"color:#64748b;font-size:13px\">Vous recevrez un rappel à J-15, J-7, J-3 et J-1.</p>")
    send = email("Envoyer le rappel", "={{ " + b + ".email }}",
                 "={{ " + b + ".palier === 'enregistrement' ? 'Échéance enregistrée : ' : 'Rappel J-' + " + b + ".jours_restants + ' : ' }}"
                 "répondre à {{ " + b + ".reference }} avant le {{ " + b + ".date_limite }}", "=" + html, (0, 0))
    return webhook_flow("JISER · Rappel d'échéance (envoyé par l'API)", "jiser-rappel", send)


def reminders_workflow() -> dict:
    trigger = node("Chaque jour à 8h", "n8n-nodes-base.scheduleTrigger", 1.2,
                   {"rule": {"interval": [{"field": "cronExpression", "expression": "0 8 * * *"}]}}, (0, 0))
    fetch = node("Échéances à 7 jours", "n8n-nodes-base.httpRequest", 4.2, {
        "url": f"{API}/api/n8n/echeances?jours=7", "sendHeaders": True,
        "headerParameters": {"parameters": [{"name": "X-Jiser-Secret", "value": SECRET}]}, "options": {}}, (240, 0))
    html = page("Rappel : répondez avant le {{ $json.date_limite }}",
                "<p>Bonjour {{ $json.prenom }},</p>"
                "<p>Il vous reste <b>{{ $json.jours_restants }} jour(s)</b> pour répondre à la notification "
                "<b>{{ $json.reference }}</b> ({{ $json.entreprise }}). Passé ce délai, la taxation peut être établie d'office "
                "(articles 44 et 47 du CDPF).</p>"
                "<p>Connectez-vous à JISER pour retrouver l'analyse et le brouillon de réponse.</p>")
    send = email("Envoyer le rappel", "={{ $json.email }}",
                 "=Plus que {{ $json.jours_restants }} jour(s) pour répondre à {{ $json.reference }}", "=" + html, (480, 0))
    return {
        "name": "JISER · Rappels des délais de réponse", "nodes": [trigger, fetch, send],
        "connections": {
            trigger["name"]: {"main": [[{"node": fetch["name"], "type": "main", "index": 0}]]},
            fetch["name"]: {"main": [[{"node": send["name"], "type": "main", "index": 0}]]},
        },
        "settings": {"executionOrder": "v1"}, "active": False,
    }


def main() -> None:
    """`--local EMAIL`: bake the real secret (from .env) and sender into n8n/local/ (git-ignored)."""
    global OUT, SECRET, FROM, USE_GMAIL
    if len(sys.argv) >= 2 and sys.argv[1] in ("--local", "--cloud"):
        from dotenv import dotenv_values
        SECRET = dotenv_values(ROOT / ".env").get("N8N_SHARED_SECRET") or SECRET
        if sys.argv[1] == "--cloud":
            USE_GMAIL = True
        else:
            FROM = f"JISER <{sys.argv[2]}>"
        OUT = ROOT / "n8n" / "local"
    OUT.mkdir(parents=True, exist_ok=True)
    for fname, wf in (("jiser-otp.json", otp_workflow()), ("jiser-bienvenue.json", welcome_workflow()),
                      ("jiser-rappels.json", reminders_workflow()), ("jiser-rappel-push.json", reminder_push_workflow())):
        (OUT / fname).write_text(json.dumps(wf, ensure_ascii=False, indent=2), encoding="utf-8")
        print("written", OUT / fname)


if __name__ == "__main__":
    main()
