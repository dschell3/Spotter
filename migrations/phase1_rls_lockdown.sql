-- Phase 1 deadbolt: deny ALL PostgREST access to application tables.
-- The Flask server uses the service_role key, which bypasses RLS.
-- The browser anon key remains valid for Supabase Auth endpoints only.
--
-- RUN ORDER: only after the service-role code (config.py/db.py changes) is
-- deployed to production. Running this first takes the app down.

do $$
declare r record;
begin
  -- Drop every existing policy in public (old per-user policies included)
  for r in
    select schemaname, tablename, policyname
    from pg_policies where schemaname = 'public'
  loop
    execute format('drop policy if exists %I on %I.%I',
                   r.policyname, r.schemaname, r.tablename);
  end loop;

  -- Enable RLS on every table in public; with no policies, this denies everything
  for r in
    select schemaname, tablename
    from pg_tables where schemaname = 'public'
  loop
    execute format('alter table %I.%I enable row level security',
                   r.schemaname, r.tablename);
  end loop;
end $$;

-- Belt and suspenders: revoke direct privileges from the API roles.
-- (No client-side code queries tables or calls RPCs; only supabase.auth is used.)
revoke all on all tables    in schema public from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;
revoke all on all functions in schema public from anon, authenticated;
alter default privileges in schema public revoke all on tables    from anon, authenticated;
alter default privileges in schema public revoke all on sequences from anon, authenticated;
alter default privileges in schema public revoke all on functions from anon, authenticated;
