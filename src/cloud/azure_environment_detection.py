import requests
import os
from typing import Optional, Dict


class AzureEnvironmentDetector:
    METADATA_URL = "http://169.254.169.254/metadata/instance"
    API_VERSION = "2021-02-01"

    @classmethod
    def get_azure_metadata(cls) -> Optional[Dict]:
        """
        Retrieve Azure instance metadata if running in Azure.
        Returns None if not running in Azure.
        """
        try:
            headers = {'Metadata': 'true'}
            params = {'api-version': cls.API_VERSION}
            response = requests.get(
                cls.METADATA_URL,
                headers=headers,
                params=params,
                timeout=2  # Short timeout to quickly detect if not in Azure
            )
            return response.json() if response.status_code == 200 else None
        except requests.RequestException:
            return None

    @classmethod
    def get_environment_info(cls) -> Dict[str, str]:
        """
        Get information about the current environment.

        1. Tries Azure instance metadata (valid for VM, AKS, ACI).
        2. Checks App Service environment variables (WEBSITE_RESOURCE_GROUP).
        3. Falls back to environment variable AZURE_ENVIRONMENT or 'dev'.

        Returns:
            Dict[str, str]: A dictionary with keys:
                            - "is_azure": "True" or "False"
                            - "environment": dev, stage, or prod
        """
        metadata = cls.get_azure_metadata()

        # Case 1: Metadata is available => likely running in VM/AKS/ACI
        if metadata and "compute" in metadata:
            resource_group_name = metadata["compute"].get("resourceGroupName", "")
            environment = cls.extract_environment(resource_group_name)
            project_name = cls.extract_project_name(resource_group_name)
            return {
                "is_azure": True,
                "environment": environment,
                "project_name": project_name
            }

        # Case 2: Check App Service environment variables
        website_rg = os.getenv("WEBSITE_RESOURCE_GROUP")
        if website_rg:
            # We are likely on Azure App Service
            environment = cls.extract_environment(website_rg)
            project_name = cls.extract_project_name(website_rg)
            return {
                "is_azure": True,
                "environment": environment,
                "project_name": project_name
            }

        # Case 3: Not on Azure or environment is unknown => fallback
        fallback_env = os.getenv("AZURE_ENVIRONMENT", "dev")
        fallback_project_name = os.getenv("AZURE_PROJECT_NAME", "ai4accountancy")
        return {
            "is_azure": False,
            "environment": fallback_env,
            "project_name": fallback_project_name
        }

    @classmethod
    def extract_environment(cls, resource_group_name):
        if 'dev' in resource_group_name:
            environment = 'dev'
        elif 'stage' in resource_group_name:
            environment = 'stage'
        elif 'prod' in resource_group_name:
            environment = 'prod'
        else:
            raise ValueError(f"Unknown environment for resource group: {resource_group_name}")

        return environment

    @classmethod
    def extract_project_name(cls, resource_group_name: str):
        return resource_group_name.split('-')[1]