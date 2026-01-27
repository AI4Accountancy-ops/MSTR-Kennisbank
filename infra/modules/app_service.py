import pulumi
from pulumi_azure_native import web, keyvault, resources, authorization, insights, operationalinsights, cognitiveservices
import base64

from modules.role_assignments import assign_role, RoleDefinition, PrincipalType


def create_log_analytics_workspace(name: str, resource_group_name: pulumi.Output[str], location: str):
    """
    Creates a Log Analytics workspace resource.

    Args:
        name (str): The name of the Log Analytics workspace.
        resource_group_name (pulumi.Output[str]): The name of the resource group.
        location (str): The Azure region for the resource.

    Returns:
        pulumi.Output[str]: The ID of the created Log Analytics workspace.
    """
    workspace = operationalinsights.Workspace(
        resource_name=name,
        workspace_name=name,
        resource_group_name=resource_group_name,
        location=location,
        sku=operationalinsights.WorkspaceSkuArgs(name="PerGB2018"),
        retention_in_days=30,
    )

    return workspace


def create_application_insights(
    name: str,
    resource_group_name: pulumi.Output[str],
    location: str,
    workspace_id: pulumi.Output[str],
):
    """
    Creates an Application Insights resource and returns its instrumentation key.

    Args:
        name (str): The name of the Application Insights resource.
        resource_group_name (pulumi.Output[str]): The name of the resource group.
        location (str): The Azure region for the resource.
        workspace_id (pulumi.Output[str]): The ID of the Log Analytics workspace.

    Returns:
        pulumi.Output[str]: The instrumentation key of the created Application Insights resource.
    """
    app_insights = insights.Component(
        resource_name_=name,
        resource_name=name,
        resource_group_name=resource_group_name,
        location=location,
        application_type="web",  # Can be "web", "other", etc., based on your app type
        kind="web",
        flow_type="Bluefield",
        request_source="rest",
        retention_in_days=30,  # Adjust retention period as needed
        workspace_resource_id=workspace_id,
    )

    return app_insights


def create_app_service_plan(name: str, resource_group_name: pulumi.Output[str], location: str):
    plan = web.AppServicePlan(
        resource_name=name,
        name=name,
        resource_group_name=resource_group_name,
        location=location,
        kind="Linux",  # Specify that this is a Linux plan
        reserved=True,  # Required for Linux App Service Plans
        sku=web.SkuDescriptionArgs(
            tier="Basic", 
            name="B1",
        ),
    )
    return plan


def create_app_service(
        name: str,
        resource_group_name: pulumi.Output[str],
        location: str,
        app_service_plan_id: str,
        subscription_id: str,
        key_vault: keyvault.Vault,
        container_image_name: str,  # e.g., "<image>:<tag>"
        acr_login_server: str,  # e.g., "<acr-name>.azurecr.io"
        acr_id: str,  # Resource ID of the ACR
        acr_username: str,  # Username for the ACR
        acr_password: str,  # Password for the ACR
        app_insights_key: str,
        workspace_id: pulumi.Output[str],
):
    # Create the Web App with a system-assigned managed identity
    docker_image = pulumi.Output.all(acr_login_server, container_image_name).apply(
        lambda values: f"DOCKER|{values[0]}/{values[1]}"
    )
    acr_login_server = pulumi.Output.all(acr_login_server).apply(lambda values: f"https://{values[0]}")
    app = web.WebApp(
        resource_name=name,
        name=name,
        resource_group_name=resource_group_name,
        location=location,
        server_farm_id=app_service_plan_id,
        kind="app,linux",  # Specify Linux OS
        identity=web.ManagedServiceIdentityArgs(
            type="SystemAssigned",
        ),
        site_config=web.SiteConfigArgs(
            linux_fx_version=docker_image,
            app_settings=[
                web.NameValuePairArgs(name="WEBSITES_PORT", value="8080"),  # Specify the port the container listens on, this needs to be the same as the dockerfile
                web.NameValuePairArgs(name="DOCKER_REGISTRY_SERVER_URL", value=acr_login_server),
                web.NameValuePairArgs(name="DOCKER_REGISTRY_SERVER_USERNAME", value=acr_username),
                web.NameValuePairArgs(name="DOCKER_REGISTRY_SERVER_PASSWORD", value=acr_password),
                web.NameValuePairArgs(name="DOCKER_ENABLE_CI", value="true"),  # Enable continuous deployment
                # Logging-related settings
                web.NameValuePairArgs(name="APPINSIGHTS_INSTRUMENTATIONKEY", value=app_insights_key),
                web.NameValuePairArgs(name="WEBSITE_LOGGER_MAX_LOGS", value="5"),  # Limit the number of log files
            ],
        ),
        https_only=True,  # Enable public access over HTTPS
    )

    # Assign the AcrPull role to the App Service's managed identity
    app.identity.principal_id.apply(lambda principal_id: assign_role(scope=acr_id, principal_id=principal_id, name=name,
                                                                     role_definition=RoleDefinition.ACR_PULL_ROLE, principal_type=PrincipalType.SERVICE_PRINCIPAL))

    # Grant the Web App access to the Key Vault
    app.identity.principal_id.apply(lambda principal_id: assign_role(
        scope=key_vault.id, principal_id=principal_id, name=name, role_definition=RoleDefinition.KEY_VAULT_SECRETS_USER, principal_type=PrincipalType.SERVICE_PRINCIPAL))

    # Create a diagnostic setting for the App Service
    app.name.apply(lambda _: insights.DiagnosticSetting(
        resource_name=f"{name}-diagnostic-settings",
        name=f"{name}-diagnostic-settings",
        log_analytics_destination_type="Dedicated",
        resource_uri=pulumi.Output.all(resource_group_name, app.name).apply(
            lambda values: f"/subscriptions/{subscription_id}/resourceGroups/{values[0]}/providers/Microsoft.Web/sites/{values[1]}"
        ),
        logs=[
            insights.LogSettingsArgs(
                category_group="allLogs",  # Example: Console Logs
                enabled=True,
            ),
        ],
        workspace_id=workspace_id
    ))

    return app


def create_multi_container_app_service(
        name: str,
        resource_group_name: pulumi.Output[str],
        location: str,
        app_service_plan_id: str,
        subscription_id: str,
        key_vault: keyvault.Vault,
        acr_login_server: str,  # e.g., "<acr-name>.azurecr.io"
        acr_id: str,  # Resource ID of the ACR
        acr_username: str,  # Username for the ACR
        acr_password: str,  # Password for the ACR
        app_insights_key: str,
        workspace_id: pulumi.Output[str],
        docker_compose_content: pulumi.Output[str],
):
    """
    Creates an App Service configured for multi-container deployment using docker-compose.
    """
    # Base64 encode the docker-compose content for the linux_fx_version
    encoded_compose = docker_compose_content.apply(
        lambda content: f"COMPOSE|{base64.b64encode(content.encode()).decode()}"
    )
    
    acr_login_url = pulumi.Output.all(acr_login_server).apply(lambda values: f"https://{values[0]}")
    
    app = web.WebApp(
        resource_name=name,
        name=name,
        resource_group_name=resource_group_name,
        location=location,
        server_farm_id=app_service_plan_id,
        kind="app,linux,container",  # Specify Linux container OS
        identity=web.ManagedServiceIdentityArgs(
            type="SystemAssigned",
        ),
        site_config=web.SiteConfigArgs(
            linux_fx_version=encoded_compose,
            app_settings=[
                # Multi-container settings
                web.NameValuePairArgs(name="WEBSITES_ENABLE_APP_SERVICE_STORAGE", value="true"),
                web.NameValuePairArgs(name="DOCKER_REGISTRY_SERVER_URL", value=acr_login_url),
                web.NameValuePairArgs(name="DOCKER_REGISTRY_SERVER_USERNAME", value=acr_username),
                web.NameValuePairArgs(name="DOCKER_REGISTRY_SERVER_PASSWORD", value=acr_password),
                web.NameValuePairArgs(name="DOCKER_ENABLE_CI", value="true"),  # Enable continuous deployment
                
                # Changed WEBSITES_PORT to 80 for frontend
                web.NameValuePairArgs(name="WEBSITES_PORT", value="80"),
                
                # Container startup time
                web.NameValuePairArgs(name="WEBSITES_CONTAINER_START_TIME_LIMIT", value="600"),
                
                # Logging-related settings
                web.NameValuePairArgs(name="APPINSIGHTS_INSTRUMENTATIONKEY", value=app_insights_key),
                web.NameValuePairArgs(name="APPLICATIONINSIGHTS_CONNECTION_STRING", 
                                     value=pulumi.Output.concat("InstrumentationKey=", app_insights_key)),
                web.NameValuePairArgs(name="WEBSITE_LOGGER_MAX_LOGS", value="5"),
            ],
            always_on=True,
            http20_enabled=True,
        ),
        https_only=True,  # Enable public access over HTTPS
    )

    # Note: We're keeping these role assignment calls but they will be recreated
    # with new IDs after the deployment. You'll also need to manually recreate them.
    app.identity.principal_id.apply(
        lambda principal_id: assign_role(
            scope=acr_id, 
            principal_id=principal_id, 
            name=name,
            role_definition=RoleDefinition.ACR_PULL_ROLE, 
            principal_type=PrincipalType.SERVICE_PRINCIPAL
        )
    )

    if key_vault:
        app.identity.principal_id.apply(
            lambda principal_id: assign_role(
                scope=key_vault.id, 
                principal_id=principal_id, 
                name=name, 
                role_definition=RoleDefinition.KEY_VAULT_SECRETS_USER, 
                principal_type=PrincipalType.SERVICE_PRINCIPAL
            )
        )

    # Create a diagnostic setting for the App Service
    app.name.apply(
        lambda _: insights.DiagnosticSetting(
            resource_name=f"{name}-diagnostic-settings",
            name=f"{name}-diagnostic-settings",
            log_analytics_destination_type="Dedicated",
            resource_uri=pulumi.Output.all(resource_group_name, app.name).apply(
                lambda values: f"/subscriptions/{subscription_id}/resourceGroups/{values[0]}/providers/Microsoft.Web/sites/{values[1]}"
            ),
            logs=[
                insights.LogSettingsArgs(
                    category_group="allLogs",
                    enabled=True,
                ),
            ],
            workspace_id=workspace_id
        )
    )

    return app
