-- Run this SQL in Supabase SQL Editor before starting notification-service.
create extension if not exists "pgcrypto";

create table if not exists public.notifications (
    id uuid primary key default gen_random_uuid(),
    user_id integer not null,
    notification_type text not null default 'system'
        check (notification_type in ('order', 'payment', 'shipping', 'promotion', 'review', 'system')),
    channel text not null default 'in_app'
        check (channel in ('in_app', 'email', 'sms')),
    title text not null,
    message text not null,
    order_id integer,
    metadata jsonb not null default '{}'::jsonb,
    read_at timestamptz,
    created_at timestamptz not null default now()
);

create index if not exists notifications_user_created_idx
    on public.notifications (user_id, created_at desc);

create index if not exists notifications_user_unread_idx
    on public.notifications (user_id)
    where read_at is null;
