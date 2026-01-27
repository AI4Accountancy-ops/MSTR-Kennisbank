"""Repository for Postgres CRUD operations on the `chat_history` table.

This module provides a high-level, connection-pooled interface for creating,
reading, updating, deleting and searching chat conversations that were
previously stored in Cosmos DB. All nested arrays/objects are persisted as
JSONB and timestamps are normalized to ISO8601 strings for API compatibility.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
import contextlib

import psycopg2
import psycopg2.pool
import psycopg2.extras as pg_extras

from config.settings import get_settings
from logger.logger import Logger
from services.db import get_connection


logger = Logger.get_logger(__name__)


class ChatHistoryRepository:
    """Handles CRUD, search, and timestamp normalization for `chat_history`.

    Connections are managed via a psycopg2 `SimpleConnectionPool`. Each public
    method that touches the database opens a connection through the context
    manager, performs the work, and commits or rolls back on error.
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

    def upsert_chat(
        self,
        chat_id: str,
        user_id: str,
        title: str,
        messages: List[Dict[str, Any]],
        created_at: Optional[str] = None,
    ) -> Optional[str]:
        """Insert or update a chat row by primary key.

        Args:
            chat_id: UUID string for the chat (primary key).
            user_id: ID of the owner user; stored in `user_id` and `partition_key`.
            title: Chat title for listing/navigation.
            messages: Flat array of Q&A pairs as JSON-serializable dicts.
            created_at: Optional ISO8601 string to preserve original creation time.

        Returns:
            The chat ID when successful, otherwise None.
        """
        try:
            now = datetime.now()
            created_ts = datetime.fromisoformat(created_at) if created_at else now
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO chat_history (id, partition_key, user_id, title, created_at, updated_at, messages)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            partition_key = EXCLUDED.partition_key,
                            user_id = EXCLUDED.user_id,
                            title = EXCLUDED.title,
                            created_at = EXCLUDED.created_at,
                            updated_at = EXCLUDED.updated_at,
                            messages = EXCLUDED.messages
                        RETURNING id
                        """,
                        (
                            chat_id,
                            user_id,
                            user_id,
                            title,
                            created_ts,
                            now,
                            pg_extras.Json(messages),
                        ),
                    )
                    row = cur.fetchone()
                    return row[0] if row else None
        except Exception as e:
            logger.error(f"Error upserting chat: {e}", exc_info=True)
            return None

    def _to_iso(self, value):
        """Convert datetimes to ISO8601 strings; pass through other values."""
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    def get_user_chat_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Return all chats for a user ordered by `updated_at` (desc).

        Normalizes `createdAt`/`updatedAt` to strings for the API layer.
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=pg_extras.RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT id, user_id, title, created_at as "createdAt", updated_at as "updatedAt", messages
                        FROM chat_history
                        WHERE user_id = %s
                        ORDER BY updated_at DESC
                        """,
                        (user_id,),
                    )
                    rows = cur.fetchall()
                    result = []
                    for r in rows:
                        item = dict(r)
                        item["createdAt"] = self._to_iso(item.get("createdAt"))
                        item["updatedAt"] = self._to_iso(item.get("updatedAt"))
                        result.append(item)
                    return result
        except Exception as e:
            logger.error(f"Error retrieving chat history: {e}", exc_info=True)
            return []

    def get_chat_by_id(self, chat_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single chat by `id` constrained to its `user_id`."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=pg_extras.RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT id, user_id, title, created_at as "createdAt", updated_at as "updatedAt", messages
                        FROM chat_history
                        WHERE id = %s AND user_id = %s
                        """,
                        (chat_id, user_id),
                    )
                    row = cur.fetchone()
                    if not row:
                        return None
                    item = dict(row)
                    item["createdAt"] = self._to_iso(item.get("createdAt"))
                    item["updatedAt"] = self._to_iso(item.get("updatedAt"))
                    return item
        except Exception as e:
            logger.error(f"Error retrieving chat by id: {e}", exc_info=True)
            return None

    def delete_chat(self, chat_id: str, user_id: str) -> bool:
        """Delete a chat by `id` and `user_id`. Returns True if a row was removed."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM chat_history WHERE id = %s AND user_id = %s",
                        (chat_id, user_id),
                    )
                    return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting chat: {e}", exc_info=True)
            return False

    def update_chat_title(self, chat_id: str, new_title: str, user_id: str) -> bool:
        """Update the chat title and touch `updated_at`. Returns True on success."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE chat_history SET title = %s, updated_at = %s WHERE id = %s AND user_id = %s",
                        (new_title, datetime.now(), chat_id, user_id),
                    )
                    return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating chat title: {e}", exc_info=True)
            return False

    def search_chat_history(self, user_id: str, query: str) -> List[Dict[str, Any]]:
        """Search chats by title and message content for a user.

        Performs case-insensitive LIKE on `title` and scans `messages` JSONB
        for matches in `user` or `assistant` fields.
        """
        try:
            pattern = f"%{query}%"
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=pg_extras.RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT id, user_id, title, created_at as "createdAt", updated_at as "updatedAt", messages
                        FROM chat_history
                        WHERE user_id = %s
                          AND (
                            title ILIKE %s OR
                            EXISTS (
                              SELECT 1
                              FROM jsonb_array_elements(messages) AS e
                              WHERE (e->>'user') ILIKE %s OR (e->>'assistant') ILIKE %s
                            )
                          )
                        ORDER BY updated_at DESC
                        """,
                        (user_id, pattern, pattern, pattern),
                    )
                    rows = cur.fetchall()
                    result = []
                    for r in rows:
                        item = dict(r)
                        item["createdAt"] = self._to_iso(item.get("createdAt"))
                        item["updatedAt"] = self._to_iso(item.get("updatedAt"))
                        result.append(item)
                    return result
        except Exception as e:
            logger.error(f"Error searching chat history: {e}", exc_info=True)
            return []
