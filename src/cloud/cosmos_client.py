from typing import List, Dict, Optional

from azure.cosmos import CosmosClient, PartitionKey, DatabaseProxy

import definitions.names as n
from definitions.credentials import Credentials
from logger.logger import Logger

logger = Logger.get_logger(__name__)


class AzureCosmosClient:
    def __init__(
            self,
            container_name: str,
            database_name: str = n.COSMOS_DATABASE_NAME,
            cosmos_endpoint: Optional[str] = None,
            cosmos_key: Optional[str] = None,
    ):
        self.client = CosmosClient(
            cosmos_endpoint or Credentials.get_azure_cosmos_endpoint(),
            cosmos_key or Credentials.get_azure_cosmos_key(),
        )
        self.database = self.client.get_database_client(database_name)
        self.container = self.database.get_container_client(container_name)

    """
    Basic methods
    """

    def query_items(self, query: str):
        try:
            items = self.container.query_items(
                query=query,
                enable_cross_partition_query=True
            )
            return list(items)
        except Exception as e:
            logger.error(f"An error occurred while querying items: {e}")
            return []

    def upsert_item(self, item: Dict) -> bool:
        try:
            self.container.upsert_item(body=item)
            return True
        except Exception as e:
            logger.error(f"Error upserting item: {str(e)}")
            if hasattr(e, 'message'):
                logger.error(f"Detailed error message: {e.message}")
            return False

    def get_item(self, id: str):
        return self.container.read_item(id, partition_key=id)

    def get_all_items(self) -> List[Dict]:
        try:
            # Query to select all documents in the container
            item_query = "SELECT * FROM c"
            items = self.container.query_items(query=item_query, enable_cross_partition_query=True)
            return list(items)
        except Exception as e:
            logger.error(f"An error occurred while getting all items: {e}")
            return []

    def delete_item(self, item_or_id, partition_key: Optional[str] = None) -> bool:
        try:
            # Prepare candidate (id, pk) pairs to try in order. This makes deletion
            # resilient across containers partitioned by '/id' or '/partitionKey'.
            candidates: List[tuple] = []

            if isinstance(item_or_id, dict):
                item_id = item_or_id.get("id")
                pk_candidates = []

                # 1) Use explicitly provided partition key if present
                if partition_key is not None:
                    pk_candidates.append(partition_key)

                # 2) Try with id first (works when container is partitioned on '/id')
                if item_id:
                    pk_candidates.append(item_id)

                # 3) Then common fields used as partition keys in this app
                for key in ("partitionKey", "userId"):
                    val = item_or_id.get(key)
                    if val:
                        pk_candidates.append(val)

                # De-duplicate while preserving order
                seen = set()
                pk_candidates = [x for x in pk_candidates if not (x in seen or seen.add(x))]

                for pk in pk_candidates:
                    candidates.append((item_id, pk))
            else:
                item_id = item_or_id
                pk = partition_key if partition_key is not None else item_or_id
                candidates.append((item_id, pk))

            last_error: Optional[Exception] = None
            for cand_id, cand_pk in candidates:
                try:
                    self.container.delete_item(item=cand_id, partition_key=cand_pk)
                    return True
                except Exception as e:
                    last_error = e
                    # Try next candidate
                    continue

            if last_error:
                logger.error(f"An error occurred while deleting item after trying candidates: {last_error}")
            return False
        except Exception as e:
            logger.error(f"An error occurred while deleting item: {e}")
            return False

    def delete_items(self, query: str, partition_key: str):
        try:
            # Query to select all documents in the container
            for item in self.container.query_items(
                query=query,
                enable_cross_partition_query=True
            ):
                # Delete each item using its id and partition key
                self.container.delete_item(item['id'], partition_key=item[partition_key])
        except Exception as e:
            logger.error(f"An error occurred while deleting items: {e}")

    def delete_all_items(self):
        try:
            # Query to select all documents in the container
            item_query = "SELECT c.id, c.partitionKey FROM c"
            for item in self.container.query_items(query=item_query, enable_cross_partition_query=True):
                self.container.delete_item(item['id'], partition_key=item['partitionKey'])
            logger.info("All items have been deleted.")
        except Exception as e:
            logger.error(f"An error occurred while deleting items: {e}")

    def create_container(self, container_name: str, partition_key: str) -> str:
        database: DatabaseProxy = self.client.get_database_client(self.database.id)
        container = database.create_container_if_not_exists(
            id=container_name,
            partition_key=PartitionKey(path=partition_key)
        )
        return container

    # TODO[SM]: Implement a method to handle pagination for large result sets
    # TODO[SM]: Add support for bulk operations to improve performance when dealing with multiple items
    # TODO[SM]: Implement a method to handle data migration or schema updates


