import uuid
from typing import Optional, Union
from enum import Enum

import pulumi
from pulumi_azure_native import authorization
from pulumi_azuread import get_user


class RoleDefinition(Enum):
    """
    Enum to map well-known role names to their Azure role definition IDs.

    Add or modify entries as needed to support additional roles.
    """
    OWNERS = "/providers/Microsoft.Authorization/roleDefinitions/8e3af657-a8ff-443c-a75c-2fe8c4bcb635"
    CONTRIBUTORS = "/providers/Microsoft.Authorization/roleDefinitions/b24988ac-6180-42a0-ab88-20f7382dd24c"
    READERS = "/providers/Microsoft.Authorization/roleDefinitions/acdd72a7-3385-48ef-bd42-f606fba81ae7"

    KEY_VAULT_ADMINISTRATOR = "/providers/Microsoft.Authorization/roleDefinitions/00482a5a-887f-4fb3-b363-3b7fe8e74483"
    KEY_VAULT_SECRETS_OFFICER = "/providers/Microsoft.Authorization/roleDefinitions/b86a8fe4-44ce-4948-aee5-eccb2c155cd7"
    KEY_VAULT_SECRETS_USER = "/providers/Microsoft.Authorization/roleDefinitions/4633458b-17de-408a-b874-0445c86b69e6"
    KEY_VAULT_CERTIFICATES_OFFICER = "/providers/Microsoft.Authorization/roleDefinitions/a4417e6f-fecd-4de8-b567-7b0420556985"
    KEY_VAULT_CRYPTO_OFFICER = "/providers/Microsoft.Authorization/roleDefinitions/14b46e9e-c2b7-41b4-b07b-48a6ebf60603"
    KEY_VAULT_CRYPTO_USER = "/providers/Microsoft.Authorization/roleDefinitions/12338af0-0e69-4776-bea7-57ae8d297424"

    STORAGE_BLOB_DATA_OWNER = "/providers/Microsoft.Authorization/roleDefinitions/b7e6dc6d-f1e8-4753-8033-0f276bb0955b"
    STORAGE_BLOB_DATA_CONTRIBUTOR = "/providers/Microsoft.Authorization/roleDefinitions/ba92f5b4-2d11-453d-a403-e96b0029c9fe"
    STORAGE_BLOB_DATA_READER = "/providers/Microsoft.Authorization/roleDefinitions/2a2b9908-6ea1-4ae2-8e65-a410df84e7d1"

    ACR_PULL_ROLE = f"/providers/Microsoft.Authorization/roleDefinitions/7f951dda-4ed3-4680-a7ca-43fe172d538d"  # AcrPull role

    LOGIC_APP_CONTRIBUTOR = "/providers/Microsoft.Authorization/roleDefinitions/b24988ac-6180-42a0-ab88-20f7382dd24c"

    @staticmethod
    def from_name(role_name: str) -> Optional["RoleDefinition"]:
        """
        Get a RoleDefinition enum member from a role name (e.g. 'owners', 'readers', etc.).

        :param role_name: The name of the role as a string (e.g. 'owners', 'key_vault_administrator').
        :return: The corresponding RoleDefinition member if found, otherwise None.
        """
        # Convert the role name to uppercase and snake case to match enum naming convention.
        # For example: 'Key Vault Administrator' -> 'KEY_VAULT_ADMINISTRATOR'
        normalized_role = role_name.upper().replace(" ", "_")
        return getattr(RoleDefinition, normalized_role, None)


class PrincipalType(Enum):
    """
    Enum to represent the type of principal for a role assignment.

    Add or modify entries as needed to support additional principal types.
    """
    USER = "User"
    SERVICE_PRINCIPAL = "ServicePrincipal"
    GROUP = "Group"
    SYSTEM_ASSIGNED_IDENTITY = "SystemAssignedIdentity"
    MANAGED_IDENTITY = "ManagedIdentity"

    @staticmethod
    def from_name(principal_type: str) -> Optional["PrincipalType"]:
        """
        Get a PrincipalType enum member from a principal type name (e.g. 'User', 'ServicePrincipal', etc.).

        :param principal_type: The name of the principal type as a string (e.g. 'User', 'ServicePrincipal').
        :return: The corresponding PrincipalType member if found, otherwise None.
        """
        return getattr(PrincipalType, principal_type, None)


def role_assignment_exists(scope: str, role_assignment_name: str) -> bool:
    """
    Checks if a role assignment with the given name exists at the specified scope.

    :param scope: The scope at which to check for the existence of the role assignment.
    :param role_assignment_name: The name (GUID) of the role assignment.
    :return: True if the role assignment exists, False otherwise.
    """
    try:
        authorization.get_role_assignment(
            scope=scope,
            role_assignment_name=role_assignment_name
        )
        return True
    except Exception:
        return False


def get_user_object_id(user_principal_name: str) -> Optional[str]:
    """
    Get the object ID for a user using their User Principal Name (email)
    """
    try:
        # Look up the user in Azure AD
        user = get_user(user_principal_name=user_principal_name)
        return user.id.split('/')[-1]
    except Exception as e:
        pulumi.log.warn(f"Failed to find user {user_principal_name}: {str(e)}")
        return None


def assign_role(scope: Union[str, pulumi.Output[str]], principal_id: str, name: str, role_definition: RoleDefinition,
                principal_type: PrincipalType = PrincipalType.USER, import_if_exists: bool = True) -> authorization.RoleAssignment:
    """
    Assigns an Azure role to a principal at the specified scope.
    """
    safe_email = name

    # We won't finalize resource_name or do logging until we have the final string value of scope
    def create_role_assignment(s: str) -> authorization.RoleAssignment:
        # Now 's' is a plain string since we are inside apply
        resource_name = f"role-assignment-{safe_email}-{role_definition.name.lower()}"

        # Create a stable, deterministic UUID for the role assignment
        role_assignment_guid = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"{principal_id}{role_definition.value}{s}"
            )
        )

        # Determine if the role assignment exists
        exists = role_assignment_exists(s, role_assignment_guid)
        opts = pulumi.ResourceOptions()
        if exists and import_if_exists:
            opts.import_ = f"{s}/providers/Microsoft.Authorization/roleAssignments/{role_assignment_guid}"

        return authorization.RoleAssignment(
            resource_name=resource_name,
            principal_id=principal_id,
            principal_type=principal_type.value,
            role_definition_id=role_definition.value,
            scope=s,
            role_assignment_name=role_assignment_guid,
            opts=opts
        )

    # If scope is an Output, apply the function after the value is resolved
    if isinstance(scope, pulumi.Output):
        return scope.apply(lambda s: create_role_assignment(s))
    else:
        # If scope is already a string, just create directly
        return create_role_assignment(scope)

