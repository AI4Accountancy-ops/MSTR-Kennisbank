import os
import sys
import contextlib

import psycopg2
import psycopg2.pool

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

# Add src directory to Python path to make it the root for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
sys.path.insert(0, src_path)


def get_env_connection_string() -> str:
    # First, try existing environment
    conn = os.getenv("POSTGRESQL_CONNECTION_STRING")
    if conn:
        return conn

    # Fallback: load variables from src/.env if available
    src_env_path = os.path.join(os.path.dirname(src_path), "src", ".env")
    if load_dotenv is not None and os.path.isfile(src_env_path):
        load_dotenv(dotenv_path=src_env_path)
        conn = os.getenv("POSTGRESQL_CONNECTION_STRING")
        if conn:
            return conn

    # Final fallback: try repo root .env
    repo_root_env = os.path.join(os.path.dirname(os.path.dirname(src_path)), ".env")
    if load_dotenv is not None and os.path.isfile(repo_root_env):
        load_dotenv(dotenv_path=repo_root_env)
        conn = os.getenv("POSTGRESQL_CONNECTION_STRING")
        if conn:
            return conn

    raise RuntimeError(
        "POSTGRESQL_CONNECTION_STRING env var is required to create tables"
    )


class ExtraTablesCreator:
    """Create Postgres tables that mirror Cosmos containers (minimal schema).

    Tables:
      - chat_history
      - whitelist
      - feedback_chat

    Notes:
      - Nested objects/arrays (e.g., messages, emails, chat_interactions, metadata)
        are stored as JSONB columns by design.
      - Follows the same psycopg2 connection pool pattern used elsewhere in the codebase.
    """

    def __init__(self, dsn: str):
        self.connection_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            dsn=dsn,
        )

    def __del__(self):
        if hasattr(self, "connection_pool"):
            self.connection_pool.closeall()

    @contextlib.contextmanager
    def get_connection(self):
        conn = None
        try:
            conn = self.connection_pool.getconn()
            yield conn
            if conn:
                conn.commit()
        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self.connection_pool.putconn(conn)

    def ensure_tables(self) -> None:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                self._create_chat_history_table(cur)
                self._create_whitelist_table(cur)
                self._create_feedback_chat_table(cur)

    def _create_chat_history_table(self, cur) -> None:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_history (
                id UUID PRIMARY KEY,
                partition_key TEXT NOT NULL,
                user_id TEXT NOT NULL,
                title TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                messages JSONB NOT NULL
            );
            """
        )

        # Helpful index for common lookups
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_chat_history_user_updated
            ON chat_history (user_id, updated_at DESC);
            """
        )

    def _create_whitelist_table(self, cur) -> None:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS whitelist (
                id UUID PRIMARY KEY,
                partition_key TEXT NOT NULL,
                emails JSONB NOT NULL,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                description TEXT
            );
            """
        )

        # Optional functional index if email existence checks become frequent
        # (kept simple here; JSONB containment queries can be indexed later with GIN)

    def _create_feedback_chat_table(self, cur) -> None:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback_chat (
                id UUID PRIMARY KEY,
                partition_key TEXT NOT NULL,
                metadata JSONB,
                feedback_text TEXT,
                chat_interactions JSONB
            );
            """
        )


def main() -> None:
    dsn = get_env_connection_string()
    creator = ExtraTablesCreator(dsn)
    creator.ensure_tables()
    print("Tables ensured: chat_history, whitelist, feedback_chat")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error creating tables: {exc}", file=sys.stderr)
        sys.exit(1)
