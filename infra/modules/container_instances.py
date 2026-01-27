from typing import Dict, Optional

import pulumi
from pulumi_azure_native import containerinstance, operationalinsights, keyvault

from modules.role_assignments import get_user_object_id, assign_role, RoleDefinition, PrincipalType


def create_container_group(
        name: str,
        resource_group: pulumi.Output[str],
        location: str,
        image: str,
        registry_server: str,
        registry_username: str,
        registry_password: str,
        key_vault_id: Optional[pulumi.Output[str]] = None,
        storage_account_id: Optional[pulumi.Output[str]] = None,
        expose_endpoint: bool = False,
        restart_policy: str = "Never"
):
    # Create a Log Analytics workspace
    workspace = operationalinsights.Workspace(
        f"{name}-workspace",
        workspace_name=f"{name}-workspace",
        resource_group_name=resource_group.name,
        location=location,
        sku=operationalinsights.WorkspaceSkuArgs(
            name="PerGB2018"
        ),
        retention_in_days=30,
    )

    # Retrieve the workspace keys to use for the container diagnostics
    workspace_keys = workspace.name.apply(
        lambda ws_name: operationalinsights.get_shared_keys(
            resource_group_name=resource_group.name,
            workspace_name=ws_name,
        )
    )

    # Initialize the container arguments
    image_name = pulumi.Output.all(registry_server).apply(
        lambda values: f"{values[0]}/{image}"
    )
    image_name.apply(lambda img: pulumi.log.info(f"Creating container group {name} with image {img}"))
    container_args = containerinstance.ContainerArgs(
        name=f"{name}-container",
        image=image_name,
        resources=containerinstance.ResourceRequirementsArgs(
            requests=containerinstance.ResourceRequestsArgs(
                cpu=1.0,
                memory_in_gb=10,
            ),
        ),
    )

    # Conditional networking configuration
    if expose_endpoint:
        # Define the ports to expose
        container_port = 8000
        dns_name_label: Optional[str] = name.lower().replace('_', '-')  # Optional DNS name label

        # Add ports to the container
        container_args.ports = [containerinstance.ContainerPortArgs(
            port=container_port
        )]

        # Define the IP address settings
        ip_address = containerinstance.IpAddressArgs(
            ports=[containerinstance.PortArgs(
                port=container_port,
                protocol="TCP"
            )],
            type="Public",
            dns_name_label=dns_name_label,  # Optional, provides a DNS name
        )
    else:
        ip_address = None

    # Prepare the arguments for the container group
    container_group_args = {
        'container_group_name': name,
        'resource_group_name': resource_group.name,
        'location': location,
        'os_type': "Linux",
        'restart_policy': restart_policy,
        'identity': containerinstance.ContainerGroupIdentityArgs(
            type="SystemAssigned",
        ),
        'containers': [container_args],
        'image_registry_credentials': [
            containerinstance.ImageRegistryCredentialArgs(
                server=registry_server,
                username=registry_username,
                password=registry_password,
            )
        ],
        'diagnostics': containerinstance.ContainerGroupDiagnosticsArgs(
            log_analytics=containerinstance.LogAnalyticsArgs(
                workspace_id=workspace.customer_id,
                workspace_key=workspace_keys.apply(lambda keys: keys.primary_shared_key),
                log_type="ContainerInsights",
            )
        ),
    }

    # Only set ip_address when expose_endpoint is True
    if ip_address:
        container_group_args['ip_address'] = ip_address

    # Create the container group
    container_group = containerinstance.ContainerGroup(
        name,
        **container_group_args
    )

    # Grant the Web App access to the Key Vault
    if key_vault_id:
        container_group.identity.principal_id.apply(lambda principal_id: assign_role(
            scope=key_vault_id, principal_id=principal_id, name=name, role_definition=RoleDefinition.KEY_VAULT_SECRETS_USER,
            principal_type=PrincipalType.SERVICE_PRINCIPAL))

    # Grant access to storage account
    if storage_account_id:
        container_group.identity.principal_id.apply(lambda principal_id: assign_role(
            scope=storage_account_id, principal_id=principal_id, name=name, role_definition=RoleDefinition.STORAGE_BLOB_DATA_CONTRIBUTOR,
            principal_type=PrincipalType.SERVICE_PRINCIPAL))

    # Grant access to the resource group
    container_group.identity.principal_id.apply(lambda principal_id: assign_role(
        scope=resource_group.id, principal_id=principal_id, name=name, role_definition=RoleDefinition.CONTRIBUTORS,
        principal_type=PrincipalType.SERVICE_PRINCIPAL))

    return container_group
