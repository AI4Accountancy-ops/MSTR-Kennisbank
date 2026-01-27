from functools import lru_cache
from typing import Optional

import cohere
from pydantic_settings import BaseSettings
from pydantic import Field

import definitions.names as n
from definitions.credentials import Credentials


class LLMProviderSettings(BaseSettings):
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    max_retries: int = 3

class AzureOpenAISettings(LLMProviderSettings):
    api_key: str = Credentials.get_azure_openai_api_key()
    api_base: str = Credentials.get_azure_openai_endpoint()
    api_version: str = "2025-01-01-preview"
    default_model: str = "o3"
    reasoning_effort: str = "medium"
    embedding_model: str = "text-embedding-3-large"

class CohereSettings(BaseSettings):
    """Settings for Cohere API."""
    api_key: str = Credentials.get_cohere_api_key()

    def get_cohere_client(self) -> cohere.Client:
        """
        Instantiate the Cohere client with the API key.

        Returns:
            cohere.Client: The Cohere API client instance.
        """
        if not self.api_key:
            raise ValueError("Cohere API key is missing or invalid.")
        return cohere.Client(api_key=self.api_key)

class Settings(BaseSettings):
    app_name: str = "AI4Accountancy"
    azure_openai: AzureOpenAISettings = AzureOpenAISettings()
    cohere: CohereSettings = CohereSettings()
    # Add database settings
    database_url: str = Credentials.get_azure_postgresql_cnx()
    vector_store_table: str = "document_chunks"
    embedding_dimensions: int = 1536
    time_partition_interval: str = "1 day"  # Example partitioning


    search_weights: dict[str, float] = Field(default_factory=lambda: {
        "keyword": 0.3,  # Lower weight for exact matches
        "semantic": 0.5,  # Higher weight for conceptual relevance
        "rerank": 0.2,  # Fine-tuning relevance with reranking
    })


@lru_cache
def get_settings():
    return Settings()
