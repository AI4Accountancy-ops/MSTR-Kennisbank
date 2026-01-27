import uuid
from typing import Dict, List

import pulumi
from pulumi_azure_native import storage, authorization

from modules.key_vault import get_user_object_id
from modules.role_assignments import assign_role, RoleDefinition


def create_storage_account(name: str, resource_group_name: pulumi.Output[str], location: str,
                           rbac_config: Dict[str, List[str]], subscription_id: str):
    storage_account = storage.StorageAccount(
        resource_name=name,
        account_name=name,
        resource_group_name=resource_group_name,
        location=location,
        sku=storage.SkuArgs(
            name=storage.SkuName.STANDARD_LRS,
        ),
        kind=storage.Kind.STORAGE_V2,
    )

    container_name = 'data'
    container = storage.BlobContainer(
        resource_name=container_name,
        container_name=container_name,
        account_name=storage_account.name,
        resource_group_name=resource_group_name,
    )

    # Iterate over the role assignments
    for role, users in rbac_config.items():
        for user in users:
            # Lookup the user
            user_id = get_user_object_id(user)

            # Create a role assignment
            if role == 'owners':
                assign_role(
                    scope=storage_account.id,
                    role_definition=RoleDefinition.STORAGE_BLOB_DATA_OWNER,
                    principal_id=user_id,
                    name=user
                )
            elif role == 'contributors':
                assign_role(
                    scope=storage_account.id,
                    role_definition=RoleDefinition.STORAGE_BLOB_DATA_CONTRIBUTOR,
                    principal_id=user_id,
                    name=user
                )
            elif role == 'readers':
                assign_role(
                    scope=storage_account.id,
                    role_definition=RoleDefinition.STORAGE_BLOB_DATA_READER,
                    principal_id=user_id,
                    name=user
                )

    return storage_account, container


def get_storage_connection_string(
    storage_account_name: pulumi.Output[str],
    resource_group_name: pulumi.Output[str]
) -> pulumi.Output[str]:
    keys = storage.list_storage_account_keys_output(
        account_name=storage_account_name,
        resource_group_name=resource_group_name
    )
    return pulumi.Output.all(storage_account_name, keys).apply(
        lambda args: f"DefaultEndpointsProtocol=https;AccountName={args[0]};AccountKey={args[1].keys[0].value};EndpointSuffix=core.windows.net"
    )
