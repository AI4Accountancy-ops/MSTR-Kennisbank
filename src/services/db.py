import contextlib
import psycopg2
import psycopg2.pool

from config.settings import get_settings
from logger.logger import Logger


logger = Logger.get_logger(__name__)


class _GlobalPool:
    _pool = None

    @classmethod
    def get_pool(cls) -> psycopg2.pool.SimpleConnectionPool:
        if cls._pool is None:
            settings = get_settings()
            database_url = settings.database_url
            # Single process-wide pool. Keep small to avoid exhausting DB.
            cls._pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=8,
                dsn=database_url,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=3,
            )
            logger.info("Initialized global Postgres connection pool")
        return cls._pool


@contextlib.contextmanager
def get_connection():
    """Yield a healthy pooled connection with safe commit/rollback."""
    pool = _GlobalPool.get_pool()
    conn = None
    try:
        conn = pool.getconn()
        # Health check
        try:
            if conn is None or getattr(conn, "closed", 1):
                raise psycopg2.InterfaceError("stale connection")
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                _ = cur.fetchone()
        except Exception:
            if conn:
                try:
                    pool.putconn(conn, close=True)
                except Exception:
                    pass
            conn = pool.getconn()
        yield conn
        if conn and not getattr(conn, "closed", 1):
            conn.commit()
    except Exception:
        if conn and not getattr(conn, "closed", 1):
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        if conn:
            try:
                pool.putconn(conn, close=bool(getattr(conn, "closed", 0)))
            except Exception:
                pass


