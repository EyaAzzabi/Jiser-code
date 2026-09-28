"""QR codes and an A5 flyer for JISER (PDF for printing, PNG for sharing).

Usage (from the repo root):
    .venv/Scripts/python scripts/qr_flyer.py --url https://<utilisateur>-jiser.hf.space
Outputs in docs/flyer/: qr_application.png, qr_github.png, JISER_flyer_A5.pdf, JISER_flyer_A5.png
"""
from __future__ import annotations

import argparse
import base64
import io
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright
from qrcode.constants import ERROR_CORRECT_H

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "flyer"
NAVY, GOLD = (11, 47, 91), (194, 154, 46)
GITHUB = "https://github.com/EyaAzzabi/Jiser"


def qr_image(url: str, logo: bool = True) -> Image.Image:
    """Navy QR code with the JISER icon in the middle (high error correction keeps it readable)."""
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, box_size=20, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color=NAVY, back_color="white").convert("RGB")
    if logo:
        icon = Image.open(ROOT / "frontend" / "public" / "logo-icon.png").convert("RGBA")
        side = img.width // 4
        icon.thumbnail((side, side))
        pad = Image.new("RGB", (side + 24, side + 24), "white")
        ImageDraw.Draw(pad).rounded_rectangle([0, 0, pad.width - 1, pad.height - 1], radius=24, outline=GOLD, width=6)
        pad.paste(icon, ((pad.width - icon.width) // 2, (pad.height - icon.height) // 2), icon)
        img.paste(pad, ((img.width - pad.width) // 2, (img.height - pad.height) // 2))
    return img


def data_uri(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def flyer_html(url: str, qr_app: Image.Image, qr_git: Image.Image) -> str:
    logo = data_uri(Image.open(ROOT / "frontend" / "public" / "logo-icon.png"))
    features = [
        ("📷", "Photographiez votre notification", "Chaque redressement expliqué en français ou en arabe, en quelques secondes."),
        ("⚖️", "Procédure vérifiée", "8 contrôles du CDPF 2024 : les vices de procédure détectés et expliqués."),
        ("💬", "Dialogue direct et sécurisé", "Messagerie en temps réel avec l'agent qui traite votre dossier."),
        ("🏛️", "Pour l'administration", "Stock trié, score expliqué, conciliation validée par la hiérarchie."),
        ("🔒", "Confidentialité (loi 2004-63)", "Comptes vérifiés, données chiffrées, aucun nom envoyé à l'IA."),
    ]
    items = "".join(f'<div class="f"><span class="i">{i}</span><div><b>{t}</b><p>{d}</p></div></div>' for i, t, d in features)
    return f"""<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Poppins:wght@700;800&family=Tajawal:wght@700&display=swap" rel="stylesheet">
<style>
@page {{ size: A5; margin: 0 }}
* {{ margin: 0; box-sizing: border-box }}
body {{ width: 148mm; height: 210mm; font-family: Inter, sans-serif; color: #1e293b }}
.top {{ background: linear-gradient(135deg, #051a33, #0b2f5b 60%, #1d4f8f); color: #fff; padding: 10mm 10mm 8mm; position: relative; overflow: hidden }}
.top:after {{ content: ""; position: absolute; left: -20mm; right: -20mm; bottom: -52mm; height: 60mm; border-radius: 50%; border: 1mm solid rgba(194,154,46,.6) }}
.brand {{ display: flex; align-items: center; gap: 4mm }}
.brand img {{ width: 16mm; height: 16mm; background: #fff; border-radius: 4mm; padding: 1.2mm }}
h1 {{ font-family: Poppins; font-weight: 800; font-size: 30pt; letter-spacing: 1px; line-height: 1 }}
h1 span {{ color: #c29a2e }} .ar {{ font-family: Tajawal; color: #c29a2e; font-size: 20pt; margin-left: 3mm }}
.tag {{ margin-top: 3mm; font-size: 11.5pt; color: #dbe6f5 }}
.hook {{ margin-top: 5mm; font-size: 10pt; background: rgba(255,255,255,.1); border-radius: 3mm; padding: 3mm 4mm }}
.hook b {{ color: #e3c25f }}
.body {{ padding: 6mm 10mm 0 }}
.f {{ display: flex; gap: 3mm; margin-bottom: 3.2mm }} .i {{ font-size: 14pt; width: 7mm }}
.f b {{ font-family: Poppins; font-size: 10pt; color: #0b2f5b }} .f p {{ font-size: 8.5pt; color: #475569; margin-top: .6mm }}
.qr {{ display: flex; align-items: center; gap: 5mm; margin: 2mm 10mm 0; padding: 4mm; border: .6mm solid #c29a2e; border-radius: 4mm; background: #fbf7ec }}
.qr img {{ width: 34mm; height: 34mm }}
.qr b {{ font-family: Poppins; font-size: 12pt; color: #0b2f5b }} .qr p {{ font-size: 8.5pt; color: #475569; margin-top: 1mm }}
.qr code {{ font-size: 7.5pt; color: #0b2f5b; word-break: break-all }}
.foot {{ position: absolute; bottom: 6mm; left: 10mm; right: 10mm; display: flex; justify-content: space-between; align-items: center; font-size: 7.5pt; color: #64748b }}
.foot img {{ width: 14mm; height: 14mm }}
</style></head><body>
<div class="top">
  <div class="brand"><img src="{logo}"><h1>J<span>i</span>SER<span class="ar">جسر</span></h1></div>
  <div class="tag">Le pont entre le contribuable et l'administration fiscale</div>
  <div class="hook">Une notification de redressement ? <b>45 jours</b> pour répondre. JISER vous aide à comprendre, vérifier et répondre, et aide l'administration à traiter plus vite et plus juste.</div>
</div>
<div class="body">{items}</div>
<div class="qr"><img src="{data_uri(qr_app)}"><div><b>Essayez JISER</b><p>Scannez avec l'appareil photo de votre téléphone.</p><code>{url}</code></div></div>
<div class="foot"><span>Hackathon national « IA &amp; Finances publiques » 2026 · finaliste<br>L'IA explique et recommande, l'humain décide.</span>
<span style="text-align:center"><img src="{data_uri(qr_git)}"><br>Code source</span></div>
</body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="adresse publique de l'application")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    qr_app, qr_git = qr_image(args.url), qr_image(GITHUB, logo=False)
    qr_app.save(OUT / "qr_application.png")
    qr_git.save(OUT / "qr_github.png")
    html = flyer_html(args.url, qr_app, qr_git)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 560, "height": 794}, device_scale_factor=3)
        page.set_content(html)
        page.wait_for_timeout(2000)
        page.pdf(path=str(OUT / "JISER_flyer_A5.pdf"), format="A5", print_background=True)
        page.screenshot(path=str(OUT / "JISER_flyer_A5.png"), full_page=True)
        browser.close()
    print("écrit dans", OUT)


if __name__ == "__main__":
    main()
