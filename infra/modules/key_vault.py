from typing import List, Optional, Dict

import pulumi
from pulumi_azure_native import keyvault
from pulumi import Output

from modules.role_assignments import assign_role, RoleDefinition, get_user_object_id


def create_key_vault(name: str, resource_group_name: pulumi.Output[str], location: str,
                     tenant_id: str, rbac: Dict) -> keyvault.Vault:
    vault = keyvault.Vault(
        name,
        vault_name=name,
        resource_group_name=resource_group_name,
        location=location,
        properties=keyvault.VaultPropertiesArgs(
            tenant_id=tenant_id,
            enable_rbac_authorization=True,  # Enable RBAC instead of access policies
            sku=keyvault.SkuArgs(
                family="A",
                name=keyvault.SkuName.STANDARD,
            ),
            access_policies=[],  # Empty access policies since we're using RBAC
        ),
    )

    # Assign RBAC based on Config
    for role, users in rbac.items():
        for user in users:
            user_object_id = get_user_object_id(user)
            if role == 'owners':
                assign_role(scope=vault.id, role_definition=RoleDefinition.KEY_VAULT_ADMINISTRATOR, principal_id=user_object_id, name=user)
            else:
                assign_role(scope=vault.id, role_definition=RoleDefinition.KEY_VAULT_SECRETS_USER, principal_id=user_object_id, name=user)

    return vault


def add_secret(key_vault: keyvault.Vault, resource_grp: pulumi.Output[str],
               secret_name: str, secret_value: Output[str]):
    return keyvault.Secret(
        secret_name,
        properties=keyvault.SecretPropertiesArgs(
            value=secret_value,
        ),
        resource_group_name=resource_grp,
        secret_name=secret_name,
        vault_name=key_vault.name
    )


def add_key(key_vault: keyvault.Vault, resource_group: str, key_name: str):
    return keyvault.Key(
        key_name,
        key_name=key_name,
        properties=keyvault.KeyPropertiesArgs(
            kty=keyvault.JsonWebKeyType.RSA,
        ),
        resource_group_name=resource_group,
        vault_name=key_vault.name
    )