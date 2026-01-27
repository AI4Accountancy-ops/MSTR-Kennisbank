import pulumi
import pulumi_azure_native as azure_native
from pulumi import Output

from modules.role_assignments import RoleDefinition, assign_role, PrincipalType


def create_logic_app(name: str, resource_group: pulumi.Output[str], location: str, container_group_id: Output[str], subscription_id: str) -> azure_native.logic.Workflow:
    """
    Create an Azure Logic App workflow that triggers every Monday at 6:00 AM
    and starts a specified Azure Container Instance.

    Args:
        name (str): The name of the Logic App.
        resource_group (pulumi.Output[str]): The resource group name.
        location (str): The Azure region.
        container_group_id (pulumi.Output[str]): The resource ID of the container group.
        subscription_id (str): The Azure subscription ID.

    Returns:
        azure_native.logic.Workflow: The created Logic App workflow resource.
    """

    container_name = container_group_id.apply(lambda cid: cid.split("/")[-1])

    def get_workflow_definition(resource_group_name: str, container_id: str) -> dict:
        container_group_name = container_id.split("/")[-1]
        return {
            "$schema": "https://schema.management.azure.com/schemas/2016-06-01/Microsoft.Logic.json",
            "contentVersion": "1.0.0.0",
            "parameters": {
                "$connections": {
                    "type": "Object",
                    "defaultValue": {}
                }
            },
            "triggers": {
                "Recurrence": {
                    "type": "Recurrence",
                    "recurrence": {
                        "frequency": "Week",
                        "interval": 1,
                        "schedule": {
                            "hours": [6],
                            "minutes": [0],
                            "weekDays": ["Monday"]
                        }
                    }
                }
            },
            "actions": {
                "Start_containers_in_a_container_group": {
                    "type": "ApiConnection",
                    "inputs": {
                        "host": {
                            "connection": {
                                "name": "@parameters('$connections')['aci']['connectionId']"
                            }
                        },
                        "method": "post",
                        "path": f"/subscriptions/@{{encodeURIComponent('{subscription_id}')}}/resourceGroups/@{{encodeURIComponent('{resource_group_name}')}}/providers/Microsoft.ContainerInstance/containerGroups/@{{encodeURIComponent('{container_group_name}')}}/start",
                        "queries": {
                            "x-ms-api-version": "2019-12-01"
                        }
                    }
                }
            },
            "outputs": {}
        }

    def get_params(resource_group_name: str) -> dict:
        return {
            "$connections": {
                "value": {
                    "aci": {
                        "id": f"/subscriptions/{subscription_id}/providers/Microsoft.Web/locations/northeurope/managedApis/aci",
                        "connectionId": f"/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.Web/connections/aci",
                        "connectionName": "aci",
                        "connectionProperties": {
                            "authentication": {
                                "type": "ManagedServiceIdentity"
                            }
                        }
                    }
                }
            }
        }

    workflow_definition = pulumi.Output.all(resource_group.name, container_name).apply(
        lambda args: get_workflow_definition(args[0], args[1])
    )
    params = pulumi.Output.all(resource_group.name).apply(lambda args: get_params(args[0]))

    workflow = azure_native.logic.Workflow(
        name,
        workflow_name=name,
        resource_group_name=resource_group.name,
        location=location,
        definition=workflow_definition,
        # Here we set the parameter values for $connections
        parameters=params,
        identity=azure_native.logic.ManagedServiceIdentityArgs(
            type="SystemAssigned"
        ),
    )

    # Assign Contributor role to the Logic App's managed identity
    assign_role(
        scope=resource_group.id,
        principal_id=workflow.identity.principal_id,
        name=name,
        role_definition=RoleDefinition.CONTRIBUTORS,
        principal_type=PrincipalType.SERVICE_PRINCIPAL,
        import_if_exists=False
    )

    return workflow