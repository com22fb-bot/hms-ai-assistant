-- Cleanup of stale Supabase auth users that never confirmed their email.
--
-- Supabase always creates a row in auth.users on signUp; the row remains
-- with email_confirmed_at IS NULL until the user clicks the verification
-- link. This function deletes accounts that stayed unconfirmed for more
-- than 7 days so the auth table does not accumulate orphaned rows.
--
-- Schedule with pg_cron (if available) or invoke from a protected backend
-- endpoint (e.g. /admin/cleanup) on a schedule.

CREATE OR REPLACE FUNCTION public.cleanup_unverified_users()
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, auth
AS $$
DECLARE
    removed integer;
BEGIN
    WITH deleted AS (
        DELETE FROM auth.users
        WHERE email_confirmed_at IS NULL
          AND created_at < now() - interval '7 days'
        RETURNING id
    )
    SELECT count(*) INTO removed FROM deleted;
    RETURN removed;
END;
$$;

REVOKE ALL ON FUNCTION public.cleanup_unverified_users() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.cleanup_unverified_users() TO service_role;
