create table if not exists public.app_users (
  id text primary key,
  email text not null unique,
  password_hash text not null,
  organization_id text not null default 'default',
  role text not null check (role in ('Admin','Manager','Employee')),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.departments (
  id text primary key default gen_random_uuid()::text,
  organization_id text not null,
  name text not null,
  routing_keywords jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, name)
);

create table if not exists public.business_requests (
  id text primary key default gen_random_uuid()::text,
  organization_id text not null,
  sender text not null,
  subject text not null,
  message text not null,
  category text not null default 'General Inquiry',
  department text not null default 'General',
  priority text not null default 'Medium',
  status text not null default 'Pending',
  sentiment text not null default 'Neutral',
  ai_metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.agent_executions (
  id text primary key default gen_random_uuid()::text,
  organization_id text not null,
  request_id text not null references public.business_requests(id) on delete cascade,
  agent_name text not null,
  status text not null,
  input_data jsonb not null default '{}'::jsonb,
  output_data jsonb not null default '{}'::jsonb,
  error text,
  created_at timestamptz not null default now()
);

create table if not exists public.workflow_executions (
  id text primary key default gen_random_uuid()::text,
  organization_id text not null,
  request_id text not null references public.business_requests(id) on delete cascade,
  status text not null default 'Processing',
  state jsonb not null default '{}'::jsonb,
  error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.approval_records (
  id text primary key default gen_random_uuid()::text,
  organization_id text not null,
  request_id text not null references public.business_requests(id) on delete cascade,
  reviewer text,
  action text not null,
  comments text not null default '',
  draft_snapshot jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.response_drafts (
  id text primary key default gen_random_uuid()::text,
  organization_id text not null,
  request_id text not null references public.business_requests(id) on delete cascade,
  content text not null,
  approved boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.knowledge_documents (
  id text primary key default gen_random_uuid()::text,
  organization_id text not null,
  filename text not null,
  content_type text not null,
  text_content text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.audit_logs (
  id text primary key default gen_random_uuid()::text,
  organization_id text not null,
  actor text not null,
  action text not null,
  resource_type text not null,
  resource_id text,
  metadata_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists business_requests_org_status_idx on public.business_requests(organization_id,status);
create index if not exists business_requests_org_priority_idx on public.business_requests(organization_id,priority);
create index if not exists agent_executions_request_idx on public.agent_executions(request_id);
create index if not exists workflow_executions_request_idx on public.workflow_executions(request_id);
