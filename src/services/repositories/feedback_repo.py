"""Repository for Postgres operations on the `feedback_chat` table.

Supports storing full-session feedback as well as per-message like/dislike
feedback. Shapes mirror the former Cosmos documents and keep nested values
in JSONB columns for flexibility.
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


class FeedbackRepository:
    """Upsert feedback documents into the `feedback_chat` table.

    Uses a psycopg2 connection pool and JSONB for `metadata`,
    `chat_interactions`, and message-level `chat_message` payloads.
    """

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

    def upsert_feedback(self, feedback: Dict[str, Any]) -> bool:
        """Insert/update a full-session feedback document."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO feedback_chat (id, partition_key, metadata, feedback_text, chat_interactions)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                          partition_key = EXCLUDED.partition_key,
                          metadata = EXCLUDED.metadata,
                          feedback_text = EXCLUDED.feedback_text,
                          chat_interactions = EXCLUDED.chat_interactions
                        """,
                        (
                            feedback.get("id"),
                            feedback.get("partitionKey"),
                            pg_extras.Json(feedback.get("metadata")),
                            feedback.get("feedback_text"),
                            pg_extras.Json(feedback.get("chat_interactions", [])),
                        ),
                    )
                    return True
        except Exception as e:
            logger.error(f"Error upserting feedback: {e}", exc_info=True)
            return False

    def upsert_message_feedback(self, item: Dict[str, Any]) -> bool:
        """Insert/update a per-message feedback document.

        Stores `chat_message` under the `chat_interactions` column for
        consistency in a single table.
        """
        try:
            # Store message feedback into the same feedback_chat table as a separate row
            # with metadata.type = "message_feedback"
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO feedback_chat (id, partition_key, metadata, feedback_text, chat_interactions)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                          partition_key = EXCLUDED.partition_key,
                          metadata = EXCLUDED.metadata,
                          feedback_text = EXCLUDED.feedback_text,
                          chat_interactions = EXCLUDED.chat_interactions
                        """,
                        (
                            item.get("id"),
                            item.get("partitionKey"),
                            pg_extras.Json(item.get("metadata")),
                            None,
                            pg_extras.Json(item.get("chat_message")),
                        ),
                    )
                    return True
        except Exception as e:
            logger.error(f"Error upserting message feedback: {e}", exc_info=True)
            return False
