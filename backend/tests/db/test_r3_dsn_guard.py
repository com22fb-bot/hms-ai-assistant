import pytest

from tests.db.conftest import UnsafeDsn, check_safe_dsn

OK = {"R3_TEST_ALLOW_LOCAL_DB": "1"}


@pytest.mark.parametrize("dsn", [
    "postgresql://box:box@localhost/postgres",
    "postgresql://box:box@127.0.0.1:5432/postgres",
    "host=/var/run/postgresql dbname=postgres user=box",
    "dbname=r3_admin",
])
def test_permitidos(dsn):
    check_safe_dsn(dsn, OK)


@pytest.mark.parametrize("dsn", [
    "postgresql://u:p@db.tgirnpystoydvbxlvlzz.supabase.co/postgres",
    "postgresql://u:p@aws-0-us-west-2.pooler.supabase.com:6543/postgres",
    "postgresql://u:p@10.0.0.5/postgres",
    "postgresql://u:p@localhost.evil.com/postgres",
    "postgresql://u:p@localhost,db.example.com/postgres",
    "postgresql://u:p@localhost/produccion",
    "host=localhost hostaddr=10.1.1.1 dbname=postgres",
    "service=prod",
    "",
])
def test_rechazados(dsn):
    with pytest.raises(UnsafeDsn):
        check_safe_dsn(dsn, OK)


def test_requiere_opt_in():
    with pytest.raises(UnsafeDsn):
        check_safe_dsn("postgresql://box:box@localhost/postgres", {})
