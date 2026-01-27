import uuid
from typing import Dict, List, Optional
import pulumi
from pulumi_azure_native import resources, authorization

from modules.role_assignments import assign_role, RoleDefinition, get_user_object_id


def create_resource_group(name: str, location: str, role_assignments: Dict[str, List[str]]) -> resources.ResourceGroup:
    rg = resources.ResourceGroup(resource_name=name, resource_group_name=name, location=location)
    client_config = authorization.get_client_config()
    subscription_id = client_config.subscription_id
    resource_group_id = f"/subscriptions/{subscription_id}/resourceGroups/{name}"

    for role, users in role_assignments.items():
        for user_email in users:
            user_object_id = get_user_object_id(user_email)
            if user_object_id:
                assign_role(scope=resource_group_id, role_definition=RoleDefinition.from_name(role), principal_id=user_object_id, name=user_email)
            else:
                pulumi.log.warn(f"User {user_email} could not be retrieved.")

    return rg
