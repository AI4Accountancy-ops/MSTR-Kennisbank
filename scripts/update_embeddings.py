import time
from typing import List, Tuple
import uuid

from tqdm import tqdm
from psycopg2.extras import execute_values

import definitions.names as n
from services.vector_store import VectorStore
from logger.logger import Logger

logger = Logger.get_logger(__name__)

# Configuration
BATCH_SIZE = 100
MAX_RETRIES = 5
SLEEP_TIME = 5
EXPECTED_DIMENSION = 1536

# Column Names
TABLE_NAME = n.DOCUMENT_CHUNKS
ID_COLUMN = n.ID
CONTENT_COLUMN = n.CONTENT
VECTOR_COLUMN = n.VECTOR


def average_embeddings(embeddings: List[List[float]]) -> List[float]:
    """Averages multiple embeddings into a single embedding."""
    if not embeddings:
        return []
    averaged = [sum(values) / len(values) for values in zip(*embeddings)]
    return averaged

def main():
    vector_store = VectorStore()
    conn = vector_store.conn

    try:
        with conn.cursor() as cur:
            # Get total number of records
            cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME};")
            total_records = cur.fetchone()[0]
            logger.info(f"Total records to process: {total_records}")

        for offset in tqdm(range(0, total_records, BATCH_SIZE), desc="Processing Batches"):
            with conn.cursor() as cur:
                # Fetch a batch of records
                cur.execute(
                    f"""
                    SELECT {ID_COLUMN}, {CONTENT_COLUMN}
                    FROM {TABLE_NAME}
                    ORDER BY {ID_COLUMN}
                    OFFSET %s
                    LIMIT %s;
                    """,
                    (offset, BATCH_SIZE)
                )
                records = cur.fetchall()

            if not records:
                break

            id_vector_pairs: List[Tuple[str, List[float]]] = []
            for record in records:
                record_id, content = record

                # Ensure record_id is a string
                if isinstance(record_id, uuid.UUID):
                    record_id_str = str(record_id)
                elif isinstance(record_id, str):
                    # Validate UUID format
                    try:
                        uuid_obj = uuid.UUID(record_id)
                        record_id_str = str(uuid_obj)
                    except ValueError:
                        logger.error(f"Invalid UUID format for record_id: {record_id}. Skipping.")
                        continue
                else:
                    logger.error(f"Unsupported type for record_id: {type(record_id)}. Skipping.")
                    continue

                if not content:
                    logger.warning(f"Record ID {record_id_str} has no content. Skipping.")
                    continue

                retries = 0
                while retries < MAX_RETRIES:
                    try:
                        embeddings = vector_store.generate_embeddings(content)
                        # Handle multiple embeddings if returned
                        if isinstance(embeddings, list):
                            if all(isinstance(e, list) for e in embeddings):
                                if len(embeddings) > 1:
                                    embedding = average_embeddings(embeddings)
                                elif len(embeddings) == 1:
                                    embedding = embeddings[0]
                                else:
                                    embedding = []
                            else:
                                embedding = embeddings
                        else:
                            embedding = embeddings

                        if embedding and len(embedding) == EXPECTED_DIMENSION:
                            id_vector_pairs.append((record_id_str, embedding))
                            logger.debug(
                                f"Successfully generated embedding for ID {record_id_str} with dimension {len(embedding)}."
                            )
                        else:
                            actual_dim = len(embedding) if embedding else 'None'
                            logger.warning(
                                f"Embedding for ID {record_id_str} has incorrect dimension: {actual_dim}. Expected: {EXPECTED_DIMENSION}. Skipping."
                            )
                        break
                    except Exception as e:
                        retries += 1
                        logger.error(f"Error generating embedding for ID {record_id_str}: {e}")
                        if retries < MAX_RETRIES:
                            sleep_time = SLEEP_TIME * (2 ** (retries - 1))
                            logger.info(
                                f"Retrying ({retries}/{MAX_RETRIES}) after {sleep_time} seconds..."
                            )
                            time.sleep(sleep_time)
                        else:
                            logger.error(
                                f"Failed to generate embedding for ID {record_id_str} after {MAX_RETRIES} retries."
                            )
                            break

            if id_vector_pairs:
                try:
                    with conn.cursor() as cur:
                        # Prepare the SQL statement for batch updating
                        # Cast the id to UUID explicitly in WHERE clause
                        sql = f"""
                            UPDATE {TABLE_NAME} AS t 
                            SET {VECTOR_COLUMN} = v.vector::vector({EXPECTED_DIMENSION})
                            FROM (VALUES %s) AS v(id, vector)
                            WHERE t.{ID_COLUMN} = v.id::uuid;
                        """
                        template = "(%s, %s)"

                        execute_values(
                            cur,
                            sql,
                            id_vector_pairs,
                            template=template,
                            page_size=100
                        )
                    conn.commit()
                    logger.info(f"Updated {len(id_vector_pairs)} records successfully.")
                except Exception as e:
                    logger.error(f"Failed to update embeddings for batch starting at offset {offset}: {e}")
                    conn.rollback()

    finally:
        conn.close()
        logger.info("Database connection closed.")

if __name__ == "__main__":
    main()
