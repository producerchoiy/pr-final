-- 홍보 바다: Supabase SQL Editor에서 한 번만 실행하세요.
-- Streamlit에는 service_role key를 Secrets로 넣고, GitHub에는 절대 올리지 않습니다.

create table if not exists public.projects (
  id text primary key,
  name text not null,
  description text default '',
  start_date date,
  deadline date,
  department text default '',
  status text default '진행 중',
  priority text default '보통',
  memo text default '',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.categories (
  id text primary key,
  name text not null unique,
  created_at timestamptz default now()
);

create table if not exists public.tasks (
  task_id text primary key,
  title text not null,
  category text not null,
  status text not null default '기획',
  priority text not null default '보통',
  deadline date,
  execution_date date,
  start_time time,
  end_time time,
  next_action text default '',
  waiting_for text,
  waiting_type text,
  request_date timestamptz,
  followup_date timestamptz,
  description text default '',
  featured boolean default false,
  project_id text references public.projects(id) on delete set null,
  previous_status text,
  completed_at timestamptz,
  reopened_at timestamptz,
  deleted_at timestamptz,
  reminder_enabled boolean default true,
  reminder_minutes_before integer default 0,
  alarm_last_fired_at timestamptz,
  repeat_type text default 'none',
  repeat_days jsonb default '[]'::jsonb,
  repeat_start_date date,
  repeat_end_date date,
  excluded_dates jsonb default '[]'::jsonb,
  sort_order integer default 9999,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.task_steps (
  id text primary key,
  task_id text not null references public.tasks(task_id) on delete cascade,
  step_order integer not null,
  title text not null,
  completed boolean default false,
  completed_at timestamptz,
  unique(task_id, step_order)
);

create table if not exists public.task_templates (
  id text primary key,
  name text not null,
  category text not null,
  steps jsonb not null default '[]'::jsonb,
  created_at timestamptz default now()
);

create table if not exists public.waiting_items (
  id text primary key,
  task_id text not null unique references public.tasks(task_id) on delete cascade,
  waiting_for text not null,
  waiting_type text default '회신',
  requested_at timestamptz,
  followup_at timestamptz,
  completed boolean default false
);

create table if not exists public.reminders (
  id text primary key,
  title text not null,
  reminder_time time not null,
  repeat_type text default 'weekday',
  enabled boolean default true,
  created_at timestamptz default now()
);

create table if not exists public.checklists (
  id text primary key,
  title text not null,
  enabled boolean default true,
  checked_on date,
  created_at timestamptz default now()
);

create table if not exists public.content_records (
  id text primary key,
  task_id text references public.tasks(task_id) on delete set null,
  platform text default 'YouTube',
  title text not null,
  professor text default '',
  department text default '',
  content_type text default '',
  upload_date date,
  url text default '',
  memo text default '',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.task_status_history (
  id text primary key,
  task_id text not null references public.tasks(task_id) on delete cascade,
  from_status text,
  to_status text not null,
  changed_at timestamptz default now()
);

create table if not exists public.document_templates (
  id text primary key,
  name text not null,
  document_type text not null,
  content text not null default '',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.documents (
  id text primary key,
  title text not null,
  category text not null,
  department text default '',
  professor text default '',
  task_id text references public.tasks(task_id) on delete set null,
  content text default '',
  file_path text,
  file_name text,
  mime_type text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- 기존 설치에도 새 필드를 안전하게 추가합니다. 이 파일은 여러 번 실행해도 됩니다.
alter table public.projects add column if not exists start_date date;
alter table public.projects add column if not exists deadline date;
alter table public.projects add column if not exists department text default '';
alter table public.projects add column if not exists status text default '진행 중';
alter table public.projects add column if not exists priority text default '보통';
alter table public.projects add column if not exists memo text default '';
alter table public.projects add column if not exists updated_at timestamptz default now();

alter table public.tasks add column if not exists previous_status text;
alter table public.tasks add column if not exists completed_at timestamptz;
alter table public.tasks add column if not exists reopened_at timestamptz;
alter table public.tasks add column if not exists deleted_at timestamptz;
alter table public.tasks add column if not exists reminder_enabled boolean default true;
alter table public.tasks add column if not exists reminder_minutes_before integer default 0;
alter table public.tasks add column if not exists alarm_last_fired_at timestamptz;
alter table public.tasks add column if not exists repeat_type text default 'none';
alter table public.tasks add column if not exists repeat_days jsonb default '[]'::jsonb;
alter table public.tasks add column if not exists repeat_start_date date;
alter table public.tasks add column if not exists repeat_end_date date;
alter table public.tasks add column if not exists excluded_dates jsonb default '[]'::jsonb;
alter table public.tasks add column if not exists sort_order integer default 9999;
alter table public.content_records add column if not exists updated_at timestamptz default now();

create index if not exists idx_tasks_active_dates on public.tasks (deleted_at, execution_date, deadline);
create index if not exists idx_tasks_project on public.tasks (project_id);
create index if not exists idx_content_records_task on public.content_records (task_id);
create index if not exists idx_task_status_history_task on public.task_status_history (task_id, changed_at desc);

insert into storage.buckets (id, name, public)
values ('pr-documents', 'pr-documents', false)
on conflict (id) do nothing;

insert into public.categories (id, name) values
  ('CAT-01', '유튜브'), ('CAT-02', '촬영'), ('CAT-03', '편집'),
  ('CAT-04', '방송'), ('CAT-05', '사진'), ('CAT-06', '대본'),
  ('CAT-07', '콘텐츠'), ('CAT-08', '행사'), ('CAT-09', '사무 업무'), ('CAT-10', '기타')
on conflict do nothing;

insert into public.task_templates (id, name, category, steps) values
  ('TPL-EVENT-PHOTO', '행사 촬영 기본 세트', '촬영', '["촬영","촬영물 백업","사진 선별","사진 보정","해당 부서 메일 전송","포토앨범 업로드"]'::jsonb),
  ('TPL-YOUTUBE', '유튜브 인터뷰 기본 세트', '유튜브', '["질문지 작성","교수 일정 확정","촬영","영상 편집","썸네일 제작","팀장 검토","교수 검토","업로드"]'::jsonb)
on conflict (id) do nothing;

insert into public.document_templates (id, name, document_type, content) values
  ('DOC-TPL-LG', 'LG헬로비전 인터뷰 양식', 'LG헬로비전', E'[방송 제목]\n\n[오프닝]\n\n[진행자 질문]\nQ1. \nQ2. \nQ3. \n\n[교수 답변 핵심]\n\n[생활 속 실천 팁]\n\n[클로징]'),
  ('DOC-TPL-YTN', 'YTN 라디오 양식', 'YTN 라디오', E'[코너명]\n\n[오늘의 주제]\n\n[도입 멘트]\n\n[질문과 답변]\nQ1. \nA1. \n\n[청취자 주의사항]\n\n[마무리]'),
  ('DOC-TPL-YOUTUBE', '유튜브 교수 인터뷰 질문지', '유튜브 인터뷰', E'[콘텐츠 제목]\n\n[시청자가 궁금해할 핵심 질문]\n1. \n2. \n3. \n\n[오해 바로잡기]\n\n[진료가 필요한 신호]\n\n[엔딩 한 문장]'),
  ('DOC-TPL-SHORTS', '쇼츠 질문지', '쇼츠', E'[0~3초 후킹]\n\n[핵심 정보 3가지]\n1. \n2. \n3. \n\n[주의 문구]\n\n[마지막 행동 요청]')
on conflict (id) do nothing;

alter table public.projects enable row level security;
alter table public.categories enable row level security;
alter table public.tasks enable row level security;
alter table public.task_steps enable row level security;
alter table public.task_templates enable row level security;
alter table public.waiting_items enable row level security;
alter table public.reminders enable row level security;
alter table public.checklists enable row level security;
alter table public.content_records enable row level security;
alter table public.document_templates enable row level security;
alter table public.documents enable row level security;
alter table public.task_status_history enable row level security;

-- 본 앱은 Streamlit 서버의 service_role key로만 접근합니다.
-- service_role은 RLS를 우회하므로 공개 브라우저 코드나 GitHub에 노출하지 마세요.
