"""
Manuel migration 006 runner.
Docker içinde çalıştır:
  docker exec -it <container_name> python run_migration_006.py

Veya lokal:
  python run_migration_006.py
"""
import sys
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent))

from tools.pg_connection import get_conn, release_conn

SQL_PATH = Path(__file__).parent / "backend" / "migrations" / "006_sqlite_to_pg_migration.sql"


def run():
    if not SQL_PATH.exists():
        print(f"HATA: {SQL_PATH} bulunamadı")
        return

    sql = SQL_PATH.read_text(encoding="utf-8")
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            ok = 0
            fail = 0
            for stmt in sql.split(";"):
                stmt = stmt.strip()
                if not stmt or stmt.startswith("--"):
                    continue
                try:
                    cur.execute(stmt)
                    ok += 1
                except Exception as e:
                    print(f"  HATA: {e}")
                    print(f"  SQL : {stmt[:120]}...")
                    conn.rollback()
                    fail += 1
        conn.commit()
        print(f"\nMigration 006 tamamlandı: {ok} başarılı, {fail} hatalı")

        # Verify tables
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = [
                str(dict(row or {}).get("table_name") or "") for row in cur.fetchall()
            ]
            tables = [table for table in tables if table]
            print(f"\nMevcut tablolar ({len(tables)}):")
            for t in tables:
                print(f"  ✓ {t}")
    except Exception as e:
        conn.rollback()
        print(f"Migration hatası: {e}")
    finally:
        release_conn(conn)


if __name__ == "__main__":
    run()
