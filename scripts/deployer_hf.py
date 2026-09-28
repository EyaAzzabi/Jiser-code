"""Deploy JISER to Hugging Face Spaces (Docker): one public HTTPS URL for the API and the web app.

What it does:
  1. creates the Space (Docker SDK) if it does not exist;
  2. uploads the code, data and model (never .env, never node_modules);
  3. copies the secrets from .env into the Space settings (encrypted by Hugging Face, not in the code);
  4. prints the public URL. Hugging Face then builds the Docker image (about 5 to 10 minutes).

Usage (from the repo root):
    .venv/Scripts/python scripts/deployer_hf.py --space <utilisateur_hf>/jiser
The Hugging Face token (write access) is read from HF_TOKEN, or asked for without being displayed.
"""
from __future__ import annotations

import argparse
import getpass
import os
import re
from pathlib import Path

from dotenv import dotenv_values
from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[1]

# secrets copied from .env to the Space (anything else in .env stays local)
SECRETS = ["OPENAI_API_KEY", "OPENAI_MODEL", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "JISER_LLM_PROVIDER",
           "SUPABASE_URL", "SUPABASE_SERVICE_KEY", "N8N_OTP_WEBHOOK_URL", "N8N_WELCOME_WEBHOOK_URL",
           "N8N_RAPPEL_WEBHOOK_URL", "N8N_NOTIF_WEBHOOK_URL", "N8N_SHARED_SECRET", "ADMIN_EMAILS",
           "OFFICIAL_EMAIL_DOMAINS", "SEUIL_VALIDATION_CONCILIATION", "JISER_DATA_KEY"]

ALLOW = ["Dockerfile", ".dockerignore", "backend/**", "frontend/**", "data/synthetic/**", "data/legal/**",
         "data/real/**", "models/**", "scripts/**"]
IGNORE = ["**/__pycache__/**", "**/*.pyc", "frontend/node_modules/**", "frontend/dist/**", ".env", "**/.env"]


def url_du_space(space_id: str) -> str:
    owner, name = space_id.split("/")
    slug = re.sub(r"[^a-z0-9-]", "-", f"{owner}-{name}".lower())
    return f"https://{slug}.hf.space"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--space", required=True, help="identifiant du Space, ex. monnom/jiser")
    parser.add_argument("--prive", action="store_true", help="Space privé (le QR code ne fonctionnera pas pour le public)")
    args = parser.parse_args()

    token = os.getenv("HF_TOKEN") or getpass.getpass("Jeton Hugging Face (accès en écriture, non affiché) : ")
    api = HfApi(token=token)
    space, url = args.space, url_du_space(args.space)
    env = dotenv_values(ROOT / ".env")
    if not env.get("SUPABASE_URL") or not env.get("OPENAI_API_KEY"):
        raise SystemExit("Le fichier .env est incomplet (SUPABASE_URL et OPENAI_API_KEY sont nécessaires).")

    print(f"1/4 Space {space}…")
    api.create_repo(space, repo_type="space", space_sdk="docker", private=args.prive, exist_ok=True)

    print("2/4 Secrets…")
    for key in SECRETS:
        if env.get(key):
            api.add_space_secret(space, key, env[key])
    api.add_space_secret(space, "APP_URL", url)   # links in e-mails and CORS point to the public URL

    print("3/4 Envoi du code, des données et du modèle…")
    api.upload_folder(repo_id=space, repo_type="space", folder_path=ROOT, allow_patterns=ALLOW, ignore_patterns=IGNORE,
                      commit_message="Déploiement JISER")
    api.upload_file(repo_id=space, repo_type="space", path_or_fileobj=ROOT / "deploy" / "huggingface" / "README.md",
                    path_in_repo="README.md", commit_message="Présentation du Space")

    print("4/4 Terminé. Hugging Face construit maintenant l'image (5 à 10 minutes).")
    print(f"   Suivi de la construction : https://huggingface.co/spaces/{space}")
    print(f"   Application publique     : {url}")
    print(f"   Espace administrateur    : {url}/plateforme")


if __name__ == "__main__":
    main()
