-- JISER database schema for Supabase (PostgreSQL).
-- Run once in Supabase: SQL Editor > New query > paste > Run.
--
-- Security model: Row Level Security is enabled on every table and NO policy is created,
-- so the public "anon" key cannot read or write anything. Only the backend, which holds the
-- service_role key (never sent to the browser), accesses the data.

create extension if not exists pgcrypto;

-- Users created through the OTP onboarding
create table if not exists utilisateurs (
  id              uuid primary key default gen_random_uuid(),
  email           text not null unique,
  role            text not null check (role in ('entreprise', 'conseil', 'verificateur', 'contentieux', 'admin')),
  nom             text not null,
  prenom          text not null,
  fonction        text default '',
  langue          text default 'fr',
  details         jsonb not null default '{}'::jsonb,
  consentements   jsonb not null default '{}'::jsonb,
  actif           boolean not null default true,
  cree_le         timestamptz not null default now(),
  derniere_connexion timestamptz
);

-- One pending OTP per e-mail; only a salted hash of the code is stored
create table if not exists otp_codes (
  email       text primary key,
  salt        text not null,
  digest      text not null,
  expires_at  timestamptz not null,
  sent_at     timestamptz not null,
  attempts    int not null default 0,
  intention   text not null default 'inscription'
);

-- Sessions: only the SHA-256 of the bearer token is stored
create table if not exists sessions (
  token_hash      text primary key,
  email           text not null,
  role            text,
  utilisateur_id  uuid references utilisateurs(id) on delete cascade,
  expires_at      timestamptz not null,
  cree_le         timestamptz not null default now()
);

-- Notifications analysed by taxpayers (espace entreprise)
create table if not exists analyses (
  id              uuid primary key default gen_random_uuid(),
  utilisateur_id  uuid not null references utilisateurs(id) on delete cascade,
  reference       text not null,
  entreprise      text not null,
  montant_total   numeric not null,
  montant_contestable numeric not null,
  date_limite     date not null,
  nb_vices        int not null default 0,
  resultat        jsonb not null,
  cree_le         timestamptz not null default now()
);
create index if not exists analyses_user_idx on analyses (utilisateur_id, cree_le desc);
create index if not exists analyses_deadline_idx on analyses (date_limite);

-- Reply drafts
create table if not exists reponses (
  id              uuid primary key default gen_random_uuid(),
  analyse_id      uuid not null references analyses(id) on delete cascade,
  utilisateur_id  uuid not null references utilisateurs(id) on delete cascade,
  lettre          text not null,
  mode            text not null,
  cree_le         timestamptz not null default now()
);

-- Audit trail of every AI recommendation (traceability)
create table if not exists journal (
  id               bigserial primary key,
  horodatage       timestamptz not null default now(),
  action           text not null,
  cible            text not null,
  recommandation   text not null,
  mode             text not null,
  decision_humaine text not null default 'en attente',
  utilisateur      text
);

-- Contentious files (synthetic dataset for the administration space)
create table if not exists dossiers (
  id             text primary key,
  statut         text not null,
  gouvernorat    text not null,
  etape          text not null,
  montant_total  numeric not null,
  data           jsonb not null
);
create index if not exists dossiers_statut_idx on dossiers (statut);

alter table utilisateurs enable row level security;
alter table otp_codes    enable row level security;
alter table sessions     enable row level security;
alter table analyses     enable row level security;
alter table reponses     enable row level security;
alter table journal      enable row level security;
alter table dossiers     enable row level security;

-- Favourites: items a user pinned (analysis, law article, reply draft, assistant answer, admin file)
create table if not exists favoris (
  id              uuid primary key default gen_random_uuid(),
  utilisateur_id  uuid not null references utilisateurs(id) on delete cascade,
  type            text not null check (type in ('dossier', 'article', 'reponse', 'assistant', 'dossier_admin')),
  ref             text not null,
  titre           text not null,
  extrait         text not null default '',
  lien            text not null default '',
  cree_le         timestamptz not null default now(),
  unique (utilisateur_id, type, ref)
);
alter table favoris enable row level security;
