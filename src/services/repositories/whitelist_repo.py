"""Repository for Postgres operations on the `whitelist` table.

The table stores a single (or limited) set of rows with an `emails` JSONB
array. We provide helpers to upsert the document and to check membership
for a given email using JSONB containment.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import contextlib

import psycopg2
import psycopg2.pool
import psycopg2.extras as pg_extras

from config.settings import get_settings
from logger.logger import Logger
from services.db import get_connection


logger = Logger.get_logger(__name__)


class WhitelistRepository:
    """Upsert whitelist documents and perform membership checks."""

    def __init__(self):
        settings = get_settings()
        self.database_url = settings.database_url
        # Use shared DB pool via services.db

    def __del__(self):
        return

    @contextlib.contextmanager
    def get_connection(self):
        """Yield a connection from the shared pool."""
        with get_connection() as conn:
            yield conn

    def upsert_whitelist(self, item: Dict[str, Any]) -> bool:
        """Insert/update a whitelist document with emails JSONB array."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO whitelist (id, partition_key, emails, created_at, updated_at, description)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                          partition_key = EXCLUDED.partition_key,
                          emails = EXCLUDED.emails,
                          created_at = EXCLUDED.created_at,
                          updated_at = EXCLUDED.updated_at,
                          description = EXCLUDED.description
                        """,
                        (
                            item.get("id"),
                            item.get("partitionKey"),
                            pg_extras.Json(item.get("emails", [])),
                            item.get("createdAt"),
                            item.get("updatedAt"),
                            item.get("description"),
                        ),
                    )
                    return True
        except Exception as e:
            logger.error(f"Error upserting whitelist: {e}", exc_info=True)
            return False

    def is_email_whitelisted(self, email: str) -> bool:
        """Return True if the `email` exists inside any `emails` array."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Check if email exists in any whitelist.emails JSON array
                    cur.execute(
                        """
                        SELECT 1
                        FROM whitelist
                        WHERE emails @> to_jsonb(ARRAY[%s]::text[])
                        LIMIT 1
                        """,
                        (email,),
                    )
                    return cur.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking whitelist email: {e}", exc_info=True)
            return False
