import json
import os
from typing import Any, Dict

from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.keyvault.secrets import SecretClient

import definitions.names as n
from logger.logger import Logger
from cloud.azure_environment_detection import AzureEnvironmentDetector

logger = Logger.get_logger(__name__)

# VAULT
environment_info = AzureEnvironmentDetector.get_environment_info()
logger.info(f"Detected Azure environment: {environment_info}")
VAULT_URL = f"https://kv0{environment_info['project_name']}0{environment_info['environment']}.vault.azure.net/"


class Credentials:
    # Initialize with error handling so it doesn't fail immediately
    try:
        # Prefer Managed Identity when running in Azure; otherwise use DefaultAzureCredential
        if environment_info.get("is_azure"):
            kv_credential = ManagedIdentityCredential()
        else:
            kv_credential = DefaultAzureCredential(exclude_managed_identity_credential=True)
        client = SecretClient(vault_url=VAULT_URL, credential=kv_credential)
    except Exception as e:
        logger.warning(f"Failed to initialize Azure Key Vault client: {e}")
        client = None

    @classmethod
    def _get_secret(cls, secret_name):
        """
        Attempts to fetch 'secret_name' from Key Vault. If that fails, tries to
        read it as an environment variable with the same dash-lowercase name.
        If that also fails, transforms dash-lowercase to UPPERCASE_UNDERSCORES
        (e.g., 'openai-api-key' -> 'OPENAI_API_KEY') and checks again.
        """
        # First, try direct environment variable access
        # 1) Try the exact same name (e.g. "openai-api-key")
        direct_env = os.getenv(secret_name)
        if direct_env:
            return direct_env
        
        # 2) Try transformed name (e.g. 'openai-api-key' -> 'OPENAI_API_KEY')
        transformed_name = secret_name.upper().replace('-', '_')
        transformed_env = os.getenv(transformed_name)
        if transformed_env:
            return transformed_env
            
        # Only try Key Vault if client is initialized
        if cls.client:
            try:
                secret_value = cls.client.get_secret(secret_name).value
                return secret_value
            except Exception as e:
                logger.warning(f"Error fetching secret '{secret_name}' from Key Vault: {e}")
        
        # If we get here, we couldn't find the secret anywhere
        logger.error(f"Secret '{secret_name}' not found in environment variables or Key Vault")
        return ""

    # Remove the conflicting instance method version or make it call the class method
    def _get_instance_secret(self, secret_name: str) -> Any | None:
        """
        Instance version of secret retrieval (not typically used for environment fallback).
        """
        return self.__class__._get_secret(secret_name)
    
    @classmethod
    def get_stripe_api_key(cls) -> str:
        return cls()._get_secret(n.STRIPE_API_KEY)
    
    @classmethod
    def get_stripe_product_id(cls) -> str:
        return cls()._get_secret(n.STRIPE_PRODUCT_ID)

    @classmethod
    def get_subscription_sync_token(cls) -> str:
        return cls()._get_secret(n.SUBSCRIPTION_SYNC_TOKEN)

    @classmethod
    def get_stripe_webhook_secret(cls) -> str:
        return cls()._get_secret(n.STRIPE_WEBHOOK_SECRET)

    @classmethod
    def get_app_credentials(cls) -> Dict[str, str]:
        secret_json = cls()._get_secret(n.APP_CREDENTIALS)
        return json.loads(secret_json)

    # Google Credentials
    @classmethod
    def get_google_credentials_json(cls) -> str:
        return cls()._get_secret(n.GOOGLE_CREDENTIALS_JSON)

    # Slack Token
    @classmethod
    def get_slack_token(cls) -> str:
        return cls()._get_secret(n.SLACK_TOKEN)

    # Azure OpenAI
    @classmethod
    def get_azure_openai_endpoint(cls) -> str:
        return cls()._get_secret(n.AZURE_OPENAI_ENDPOINT)

    @classmethod
    def get_azure_openai_api_key(cls) -> str:
        return cls()._get_secret(n.AZURE_OPENAI_API_KEY)

    @classmethod
    def get_azure_openai_model(cls) -> str:
        return cls()._get_secret(n.AZURE_OPENAI_MODEL_NAME)

    # Azure Storage
    @classmethod
    def get_azure_storage_account_name(cls) -> str:
        return cls()._get_secret(n.AZURE_STORAGE_ACCOUNT_NAME)

    @classmethod
    def get_azure_storage_container_name(cls) -> str:
        return cls()._get_secret(n.AZURE_STORAGE_CONTAINER_NAME)

    # Azure PostgreSQL
    @classmethod
    def get_azure_postgresql_cnx(cls) -> str:
        return cls()._get_secret(n.PGVECTOR_CNX)

    @classmethod
    def get_cohere_api_key(cls) -> str:
        return cls()._get_secret(n.COHERE_API_KEY)

    # Cosmos DB
    @classmethod
    def get_azure_cosmos_whitelist_container_name(cls) -> str:
        return n.COSMOS_WHITELIST_CONTAINER_NAME

    @classmethod
    def get_azure_cosmos_feedback_container_name(cls) -> str:
        return n.COSMOS_FEEDBACK_METADATA_CONTAINER_NAME

    @classmethod
    def get_azure_cosmos_chat_history_container_name(cls) -> str:
        return n.COSMOS_CHAT_HISTORY_CONTAINER_NAME

    @classmethod
    def get_azure_cosmos_endpoint(cls) -> str:
        return cls()._get_secret(n.COSMOS_ENDPOINT)

    @classmethod
    def get_azure_cosmos_key(cls) -> str:
        return cls()._get_secret(n.COSMOS_API_KEY)

    # Scraping Credentials
    @classmethod
    def get_scraping_credentials(cls):
        secret_json = cls()._get_secret(n.SCRAPING_CREDENTIALS)
        return json.loads(secret_json)

    @classmethod
    def get_embedding_link(cls) -> str:
        return cls()._get_secret(n.EMBEDDING_LINK)



    # Admin Password
    @classmethod
    def get_admin_password(cls) -> str:
        return cls()._get_secret(n.ADMIN_PASSWORD)

    # Toggle Vector Search
    @classmethod
    def get_toggle_vector_search(cls) -> str:
        return cls()._get_secret(n.TOGGLE_VECTOR_SEARCH)


    # M365 Credentials
    @classmethod
    def get_connector_microsoft_client_id(cls) -> str:
        return cls()._get_secret(n.CONNECTOR_MICROSOFT_CLIENT_ID)

    @classmethod
    def get_connector_microsoft_client_secret(cls) -> str:
        return cls()._get_secret(n.CONNECTOR_MICROSOFT_CLIENT_SECRET)

    @classmethod
    def get_connector_microsoft_tenant_id(cls) -> str:
        return cls()._get_secret(n.CONNECTOR_MICROSOFT_TENANT_ID)

    @classmethod
    def get_connector_redirect_uri(cls) -> str:
        return cls()._get_secret(n.CONNECTOR_MICROSOFT_REDIRECT_URI)

    @classmethod
    def get_connector_client_state_secret(cls) -> str:
        return cls()._get_secret(n.CONNECTOR_MICROSOFT_CLIENT_STATE_SECRET)

    @classmethod
    def get_connector_webhook_url(cls) -> str:
        return cls()._get_secret(n.CONNECTOR_MICROSOFT_WEBHOOK_URL)