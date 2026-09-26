-- JISER migration 002: administration hierarchy, account verification, messaging, confidentiality.
-- Run once in Supabase: SQL Editor > New query > paste > Run. Safe to run twice.
-- Same security model as schema.sql: RLS enabled, no policy, only the backend (service key) accesses data.

-- 1. Administration roles (ministre, chef de centre, chargé du contentieux) and account status
alter table utilisateurs drop constraint if exists utilisateurs_role_check;
alter table utilisateurs add constraint utilisateurs_role_check
  check (role in ('entreprise', 'conseil', 'verificateur', 'contentieux', 'chef_centre', 'ministre', 'admin'));
alter table utilisateurs add column if not exists statut text not null default 'actif'
  check (statut in ('en_attente', 'actif', 'refuse', 'suspendu'));
alter table utilisateurs add column if not exists verification jsonb not null default '{}'::jsonb;

-- 2. Identity documents sent at sign-up (encrypted by the API before storage)
create table if not exists pieces_justificatives (
  id              uuid primary key default gen_random_uuid(),
  utilisateur_id  uuid not null references utilisateurs(id) on delete cascade,
  type            text not null,
  nom             text not null,
  mime            text not null,
  taille          int not null,
  contenu         text not null,
  cree_le         timestamptz not null default now()
);

-- 3. File assignment by the head of centre, and approval of large settlements
create table if not exists affectations (
  dossier_id  text primary key,
  agent_id    uuid references utilisateurs(id) on delete set null,
  agent_nom   text not null,
  par         text not null,
  cree_le     timestamptz not null default now()
);

create table if not exists conciliations (
  id              uuid primary key default gen_random_uuid(),
  dossier_id      text not null,
  reference       text not null,
  gouvernorat     text not null,
  montant_notifie numeric not null,
  montant_propose numeric not null,
  propose_par     text not null,
  statut          text not null default 'en_attente' check (statut in ('en_attente', 'validee', 'refusee')),
  decide_par      text,
  motif           text,
  decide_le       timestamptz,
  cree_le         timestamptz not null default now()
);

-- 4. Real-time messaging, one conversation per notification (contents encrypted by the API)
create table if not exists conversations (
  id                  uuid primary key default gen_random_uuid(),
  reference           text not null,
  dossier_id          text,
  analyse_id          uuid,
  entreprise_id       uuid not null references utilisateurs(id) on delete cascade,
  entreprise_nom      text not null,
  gouvernorat         text not null,
  cree_le             timestamptz not null default now(),
  dernier_message_le  timestamptz not null default now(),
  unique (reference, entreprise_id)
);

create table if not exists messages (
  id               uuid primary key default gen_random_uuid(),
  conversation_id  uuid not null references conversations(id) on delete cascade,
  auteur_id        text not null,
  auteur_role      text not null,
  auteur_nom       text not null,
  contenu          text not null,
  piece_nom        text,
  piece_mime       text,
  piece_contenu    text,
  lu_par           jsonb not null default '[]'::jsonb,
  cree_le          timestamptz not null default now()
);
create index if not exists messages_conv_idx on messages (conversation_id, cree_le);

-- 5. Access log shown to the taxpayer: who consulted which file, when and why
create table if not exists acces (
  id           bigserial primary key,
  horodatage   timestamptz not null default now(),
  reference    text not null,
  role         text not null,
  centre       text,
  action       text not null
);
create index if not exists acces_ref_idx on acces (reference, horodatage desc);

alter table pieces_justificatives enable row level security;
alter table affectations          enable row level security;
alter table conciliations         enable row level security;
alter table conversations         enable row level security;
alter table messages              enable row level security;
alter table acces                 enable row level security;
