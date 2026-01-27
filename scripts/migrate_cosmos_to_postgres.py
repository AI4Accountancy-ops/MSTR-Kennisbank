import os
import sys
import contextlib
from datetime import datetime
from typing import Any, Dict, List

import psycopg2
import psycopg2.pool
import psycopg2.extras as pg_extras
from azure.cosmos import CosmosClient

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

# Ensure local modules under `src/` are importable before local imports
src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import definitions.names as n
from definitions.credentials import Credentials


def load_envs() -> None:
    """Load environment variables from typical locations if not already set."""
    # Try src/.env first
    src_env_path = os.path.join(os.path.dirname(src_path), "src", ".env")
    if load_dotenv is not None and os.path.isfile(src_env_path):
        load_dotenv(dotenv_path=src_env_path)

    # Then fallback to repo root .env
    repo_root_env = os.path.join(os.path.dirname(os.path.dirname(src_path)), ".env")
    if load_dotenv is not None and os.path.isfile(repo_root_env):
        load_dotenv(dotenv_path=repo_root_env)


def get_pg_dsn() -> str:
    dsn = os.getenv("POSTGRESQL_CONNECTION_STRING")
    if not dsn:
        raise RuntimeError("POSTGRESQL_CONNECTION_STRING env var is required")
    return dsn


class PostgresPool:
    def __init__(self, dsn: str):
        self.pool = psycopg2.pool.SimpleConnectionPool(minconn=1, maxconn=10, dsn=dsn)

    def __del__(self):
        if hasattr(self, "pool"):
            self.pool.closeall()

    @contextlib.contextmanager
    def conn(self):
        connection = None
        try:
            connection = self.pool.getconn()
            yield connection
            if connection:
                connection.commit()
        except Exception:
            if connection:
                connection.rollback()
            raise
        finally:
            if connection:
                self.pool.putconn(connection)


def parse_ts(value: Any) -> Any:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return value  # let Postgres attempt cast


def migrate_chat_history(container, pg: PostgresPool) -> int:
    items: List[Dict[str, Any]] = list(
        container.query_items(
            query="SELECT * FROM c", enable_cross_partition_query=True
        )
    )
    if not items:
        return 0

    sql = """
        INSERT INTO chat_history (
            id, partition_key, user_id, title, created_at, updated_at, messages
        ) VALUES (
            %(id)s, %(partition_key)s, %(user_id)s, %(title)s, %(created_at)s, %(updated_at)s, %(messages)s
        )
        ON CONFLICT (id) DO UPDATE SET
            partition_key = EXCLUDED.partition_key,
            user_id = EXCLUDED.user_id,
            title = EXCLUDED.title,
            created_at = EXCLUDED.created_at,
            updated_at = EXCLUDED.updated_at,
            messages = EXCLUDED.messages;
        """

    rows = []
    for doc in items:
        rows.append(
            {
                "id": doc.get("id"),
                "partition_key": doc.get("partitionKey"),
                "user_id": doc.get("userId"),
                "title": doc.get("title"),
                "created_at": parse_ts(doc.get("createdAt")),
                "updated_at": parse_ts(doc.get("updatedAt")),
                "messages": pg_extras.Json(doc.get("messages", [])),
            }
        )

    with pg.conn() as conn:
        with conn.cursor() as cur:
            pg_extras.execute_batch(cur, sql, rows, page_size=500)

    return len(rows)


def migrate_feedback_chat(container, pg: PostgresPool) -> int:
    items: List[Dict[str, Any]] = list(
        container.query_items(
            query="SELECT * FROM c", enable_cross_partition_query=True
        )
    )
    if not items:
        return 0

    sql = """
        INSERT INTO feedback_chat (
            id, partition_key, metadata, feedback_text, chat_interactions
        ) VALUES (
            %(id)s, %(partition_key)s, %(metadata)s, %(feedback_text)s, %(chat_interactions)s
        )
        ON CONFLICT (id) DO UPDATE SET
            partition_key = EXCLUDED.partition_key,
            metadata = EXCLUDED.metadata,
            feedback_text = EXCLUDED.feedback_text,
            chat_interactions = EXCLUDED.chat_interactions;
        """

    rows = []
    for doc in items:
        rows.append(
            {
                "id": doc.get("id"),
                "partition_key": doc.get("partitionKey"),
                "metadata": (
                    pg_extras.Json(doc.get("metadata"))
                    if doc.get("metadata") is not None
                    else None
                ),
                "feedback_text": doc.get("feedback_text"),
                "chat_interactions": pg_extras.Json(doc.get("chat_interactions", [])),
            }
        )

    with pg.conn() as conn:
        with conn.cursor() as cur:
            pg_extras.execute_batch(cur, sql, rows, page_size=500)

    return len(rows)


def migrate_whitelist(container, pg: PostgresPool) -> int:
    items: List[Dict[str, Any]] = list(
        container.query_items(
            query="SELECT * FROM c", enable_cross_partition_query=True
        )
    )
    if not items:
        return 0

    sql = """
        INSERT INTO whitelist (
            id, partition_key, emails, created_at, updated_at, description
        ) VALUES (
            %(id)s, %(partition_key)s, %(emails)s, %(created_at)s, %(updated_at)s, %(description)s
        )
        ON CONFLICT (id) DO UPDATE SET
            partition_key = EXCLUDED.partition_key,
            emails = EXCLUDED.emails,
            created_at = EXCLUDED.created_at,
            updated_at = EXCLUDED.updated_at,
            description = EXCLUDED.description;
        """

    rows = []
    for doc in items:
        rows.append(
            {
                "id": doc.get("id"),
                "partition_key": doc.get("partitionKey"),
                "emails": pg_extras.Json(doc.get("emails", [])),
                "created_at": parse_ts(doc.get("createdAt")),
                "updated_at": parse_ts(doc.get("updatedAt")),
                "description": doc.get("description"),
            }
        )

    with pg.conn() as conn:
        with conn.cursor() as cur:
            pg_extras.execute_batch(cur, sql, rows, page_size=500)

    return len(rows)


def main() -> None:
    load_envs()

    # Initialize clients
    pg = PostgresPool(get_pg_dsn())

    endpoint = Credentials.get_azure_cosmos_endpoint()
    key = Credentials.get_azure_cosmos_key()
    if not endpoint or not key:
        raise RuntimeError(
            "COSMOS credentials not found via Credentials. Ensure COSMOS_ENDPOINT and COSMOS_API_KEY are set in src/.env or environment"
        )
    cosmos_client = CosmosClient(endpoint, credential=key)

    database = cosmos_client.get_database_client(n.COSMOS_DATABASE_NAME)
    chat_history_container = database.get_container_client(
        n.COSMOS_CHAT_HISTORY_CONTAINER_NAME
    )
    feedback_container = database.get_container_client(
        n.COSMOS_FEEDBACK_METADATA_CONTAINER_NAME
    )
    whitelist_container = database.get_container_client(
        n.COSMOS_WHITELIST_CONTAINER_NAME
    )

    # Migrate
    ch_count = migrate_chat_history(chat_history_container, pg)
    fb_count = migrate_feedback_chat(feedback_container, pg)
    wl_count = migrate_whitelist(whitelist_container, pg)

    print(
        f"Migrated: chat_history={ch_count}, feedback_chat={fb_count}, whitelist={wl_count}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error migrating data: {exc}", file=sys.stderr)
        sys.exit(1)
