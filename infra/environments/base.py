import os
import sys

# Changing the directory to the parent directory to also import names from there
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from dotenv import load_dotenv

import src.definitions.names as n

load_dotenv(dotenv_path="../.env")


class BaseConfig:
    env = None  # This will be set by the environment specific configurations
    subscription_id = "ed6b4971-96da-4b8b-bb0f-94b8a850204e" # Microsoft Azure Sponsorship
    tenant_id = "668af4dd-23fc-49a5-bdbe-f4c407d4368b" # Go to Azure EntraID and get this value
    github_pat = os.environ["GITHUB_PAT"] # Personal access token for GitHub: https://github.com/settings/tokens, add codespace, admin:repo_hook and workflow access, also make sure PAT's are enabled within your org
    github_repo_name = "MSTR-Projects/AI4Accountancy" # Name of the GitHub repository
    project_name = "ai4accountancy"
    location = "northeurope"

    # Storage
    enable_storage = True

    # Postgresql
    enable_postgresql = True

    # Key Vault
    enable_key_vault = True

    # CosmosDB
    enable_cosmosdb = True
    cosmos_db_name = "configs"
    cosmos_container_names = ["feedback_chat"]

    # OpenAI
    enable_openai = True
    location_openai = 'swedencentral' # eastus has all possibilities and better availability
    openai_model_name = 'gpt'

    # App Service
    enable_app_service = True

    # Containers
    enable_container_registry = True
    enable_container_instances = False
    image_tag = 'latest'

    # Budget
    enable_budget = False
    max_budget_amount = 1000  # Adjust as needed
    budget_increment = 250

    # Logic App
    enable_logic_app = False

    # Local env variables
    enable_local_env_variables = True

    @classmethod
    def get_resource_name(cls, resource_type: str):
        if resource_type in ['sa', 'kv', 'acr']:
            return f"{resource_type}0{cls.project_name}0{cls.env}"
        if resource_type in ['docker', 'ga']:
            return f"{cls.project_name}-{cls.env}"
        if resource_type == 'openai':
            return f"{resource_type}-{cls.project_name}-{cls.env}-{cls.location_openai}"
        return f"{resource_type}-{cls.project_name}-{cls.env}-{cls.location}"
