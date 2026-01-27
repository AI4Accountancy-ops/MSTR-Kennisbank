import os
import sys

# Changing the directory to the parent directory to also import names from there
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

import pulumi
from dotenv import load_dotenv
from pulumi_azure_native import  authorization
from pulumi_azure_native.cognitiveservices import list_account_keys_output
from pulumi_azure_native.documentdb import list_database_account_keys_output
from pulumi_azure_native.containerregistry import list_registry_credentials_output

import src.definitions.names as n
from cicd.create_deployment_pipeline import create_deployment_pipeline, add_secrets_to_github
from infra_definitions.enums import Environments
from modules.resource_group import create_resource_group
from modules.storage import create_storage_account, get_storage_connection_string
from modules.postgresql import create_postgresql_server, get_postgresql_connection_string
from modules.key_vault import create_key_vault, add_secret
from modules.cosmos_db import create_cosmos_db, get_cosmos_db_connection_string, create_container, create_database
from modules.openai import create_openai_account, deploy_openai_model, deploy_embedding_model
from modules.app_service import (
    create_app_service_plan, create_app_service,
    create_application_insights, create_log_analytics_workspace, create_multi_container_app_service
)
from modules.container_registry import create_container_registry, get_registry_credentials, push_docker_image
from modules.container_instances import create_container_group
from modules.budget import create_budget
from modules.logic_apps import create_logic_app


ENVIRONMENT = Environments.DEV
if ENVIRONMENT == Environments.DEV:
    from environments.development import Config
    from docker_compose_secrets import DOCKER_COMPOSE_TEMPLATE
elif ENVIRONMENT == Environments.STAGING:
    from environments.staging import Config
    from docker_compose_secrets_stage import DOCKER_COMPOSE_TEMPLATE
elif ENVIRONMENT == Environments.PRODUCTION:
    from environments.production import Config
    from docker_compose_secrets_prod import DOCKER_COMPOSE_TEMPLATE


# Create the resource group
rg = create_resource_group(
    name=Config.get_resource_name("rg"),
    location=Config.location,
    role_assignments=Config.rbacConfig
)

# Create Key Vault if enabled
key_vault = None
if Config.enable_key_vault:
    current_user = authorization.get_client_config()
    key_vault = create_key_vault(
        name=Config.get_resource_name("kv"),
        resource_group_name=rg.name,
        location=Config.location,
        tenant_id=current_user.tenant_id,
        rbac=Config.rbacConfig
    )
    pulumi.export("key_vault_name", key_vault.name)

# Create storage account if enabled
if Config.enable_storage:
    storage_account, container = create_storage_account(
        name=Config.get_resource_name('sa'),
        resource_group_name=rg.name,
        location=Config.location,
        rbac_config=Config.rbacConfig,
        subscription_id=Config.subscription_id
    )

    connection_string = get_storage_connection_string(storage_account.name, rg.name)
    pulumi.export(n.AZURE_STORAGE_ACCOUNT_NAME, storage_account.name)
    pulumi.export(n.AZURE_STORAGE_CONNECTION_STRING, connection_string)
    pulumi.export(n.AZURE_STORAGE_CONTAINER_NAME, container.name)

    if Config.enable_key_vault:
        add_secret(key_vault, rg.name, n.AZURE_STORAGE_CONNECTION_STRING, connection_string)
        add_secret(key_vault, rg.name, n.AZURE_STORAGE_CONTAINER_NAME, container.name)
        add_secret(key_vault, rg.name, n.AZURE_STORAGE_ACCOUNT_NAME, storage_account.name)

# Create PostgreSQL server if enabled
if Config.enable_postgresql:
    postgres_server, postgres_password = create_postgresql_server(
        Config.get_resource_name("psql"),
        rg.name,
        Config.location,
    )
    postgres_connection_string = get_postgresql_connection_string(
        postgres_server.fully_qualified_domain_name,
        "postgresadmin",
        postgres_password
    )
    pulumi.export("postgresql_server_name", postgres_server.name)
    pulumi.export(n.PGVECTOR_CNX, postgres_connection_string)

    if Config.enable_key_vault:
        add_secret(key_vault, rg.name, n.PGVECTOR_CNX, postgres_connection_string)


# Create Cosmos DB if enabled
if Config.enable_cosmosdb:
    cosmos_db = create_cosmos_db(
        name=Config.get_resource_name("cosmos"),
        resource_group_name=rg.name,
        location=Config.location
    )

    # Create a SQL database
    database = create_database(Config.cosmos_db_name, cosmos_db, rg)

    # Create containers
    containers = []
    for container_name in Config.cosmos_container_names:
        container = create_container(container_name, cosmos_db, database, rg)
        containers.append(container)

    cosmos_connection_string = pulumi.Output.all(cosmos_db.name, rg.name).apply(
        lambda args: get_cosmos_db_connection_string(args[0], args[1])
    )
    pulumi.export("cosmos_db_name", cosmos_db.name)
    pulumi.export("cosmos_db_connection_string", cosmos_connection_string)

    if Config.enable_key_vault:
        add_secret(key_vault, rg.name, n.COSMOS_CONNECTION_STRING, cosmos_connection_string)
        add_secret(key_vault, rg.name, n.COSMOS_ENDPOINT, cosmos_db.document_endpoint)
        keys = list_database_account_keys_output(
            account_name=cosmos_db.name,
            resource_group_name=rg.name,
        )
        primary_key = keys.apply(lambda k: k.primary_master_key)
        add_secret(key_vault, rg.name, n.COSMOS_API_KEY, primary_key)

# Create OpenAI account if enabled
if Config.enable_openai:
    openai_account = create_openai_account(
        Config.get_resource_name("openai"),
        rg.name,
        Config.location_openai
    )
    openai_model = deploy_openai_model(
        Config.openai_model_name,
        rg.name,
        openai_account.name
    )
    
    # embedding_model = deploy_embedding_model(
    #     "text-embedding-3-large",
    #     rg.name,
    #     openai_account.name
    # )

    pulumi.export("openai_account_name", openai_account.name)
    pulumi.export(n.AZURE_OPENAI_MODEL_NAME, openai_model.name)

    if Config.enable_key_vault:
        keys = list_account_keys_output(
            resource_group_name=rg.name,
            account_name=openai_account.name
        )

        # Store the API key in Key Vault
        add_secret(key_vault, rg.name, n.AZURE_OPENAI_API_KEY, keys.apply(lambda k: k.key1))
        add_secret(key_vault, rg.name, n.AZURE_OPENAI_ENDPOINT, openai_account.properties.endpoint)
        add_secret(key_vault, rg.name, n.AZURE_OPENAI_MODEL_NAME, Config.openai_model_name)

# Create Container Registry if enabled
if Config.enable_container_registry or Config.enable_app_service:
    # Create container registry
    container_registry = create_container_registry(
        Config.get_resource_name("acr"),
        rg.name,
        Config.location
    )
    registry_credentials = get_registry_credentials(container_registry.name, rg.name)

    # Push both frontend and backend Docker images to container registry
    backend_image = push_docker_image(
        container_registry=container_registry,
        registry_credentials_output=registry_credentials,
        image_name=Config.get_resource_name('backend'),
        image_tag=Config.image_tag,
        context_path="../src",
        docker_file_path="../src/Dockerfile",
        environment=Config.env
    )
    
    frontend_image = push_docker_image(
        container_registry=container_registry,
        registry_credentials_output=registry_credentials,
        image_name=Config.get_resource_name('frontend'),
        image_tag=Config.image_tag,
        context_path="../frontend",
        docker_file_path="../frontend/Dockerfile",
        environment=Config.env
    )

    pulumi.export("container_registry_name", container_registry.name)
    pulumi.export("container_registry_login_server", container_registry.login_server)
    pulumi.export("container_registry_username", registry_credentials.username)
    pulumi.export(n.CONTAINER_REGISTRY_PASSWORD, registry_credentials.passwords[0].value)
    pulumi.export("backend_image_name", backend_image.ref)
    pulumi.export("frontend_image_name", frontend_image.ref)

    if Config.enable_key_vault:
        add_secret(key_vault=key_vault, resource_grp=rg.name, secret_name=n.CONTAINER_REGISTRY_PASSWORD,
                   secret_value=registry_credentials.passwords[0].value)

    # Create CICD pipelines
    pulumi.Output.all(
        container_registry.login_server,
        registry_credentials.username,
        registry_credentials.passwords[0].value
    ).apply(
        lambda values: add_secrets_to_github(
            github_pat=Config.github_pat,
            github_repo_name=Config.github_repo_name,
            secrets={
                f"ACR_LOGIN_SERVER_{Config.env}": values[0], # TODO[SB]: make a name out of this and make it match with the template in container_registry
                f"ACR_USERNAME_{Config.env}": values[1],
                f"ACR_PASSWORD_{Config.env}": values[2]
            }
        )
    )

    pulumi.Output.all(
        backend_image.ref,
        frontend_image.ref
    ).apply(
        lambda values: create_deployment_pipeline(
            pipeline_name=Config.get_resource_name('ga'),
            template_name="container_registry",
            env=Config.env,
            url_to_image=values[0].split(Config.image_tag)[0] + Config.image_tag,
            url_to_image_frontend=values[1].split(Config.image_tag)[0] + Config.image_tag
        )
    )

    # Get the admin credentials for the container registry
    acr_credentials = list_registry_credentials_output(
        registry_name=container_registry.name,
        resource_group_name=rg.name
    )

    # Extract the admin password (first one by default)
    acr_password = acr_credentials.apply(lambda creds: creds.passwords[0].value)

    # For your docker-compose template:
    docker_compose_content = pulumi.Output.all(
        container_registry.login_server,
        cosmos_db.document_endpoint,
        primary_key,
        acr_password,
        postgres_connection_string,
        connection_string
    ).apply(
        lambda args: DOCKER_COMPOSE_TEMPLATE.format(*args)
    )

# Create App Service if enabled
if Config.enable_app_service:
    app_service_plan = create_app_service_plan(
        name=Config.get_resource_name("asp"),
        resource_group_name=rg.name,
        location=Config.location
    )

    # Create Log Analytics Workspace and Application Insights
    workspace = create_log_analytics_workspace(
        name=Config.get_resource_name("law"),
        resource_group_name=rg.name,
        location=Config.location
    )
    app_insights = create_application_insights(
        name=Config.get_resource_name("ai"),
        resource_group_name=rg.name,
        location=Config.location,
        workspace_id=workspace.id
    )

    app_service = create_multi_container_app_service(
        name=Config.get_resource_name("app"),
        resource_group_name=rg.name,
        location=Config.location,
        app_service_plan_id=app_service_plan.id,
        key_vault=key_vault,
        subscription_id=Config.subscription_id,
        acr_login_server=container_registry.login_server,
        acr_id=container_registry.id,
        acr_username=registry_credentials.username,
        acr_password=acr_password,
        app_insights_key=app_insights.instrumentation_key,
        workspace_id=workspace.id,
        docker_compose_content=docker_compose_content
    )

    # Export the app service details
    pulumi.export("app_service_name", app_service.name)
    pulumi.export("app_service_default_hostname", app_service.default_host_name)

# Create Container Instance if enabled
if Config.enable_container_instances and Config.enable_container_registry:
    container_group = create_container_group(
        Config.get_resource_name("aci"),
        rg.name,
        Config.location,
        f"{container_registry.login_server}/myapp:latest",
        container_registry.login_server,
        registry_credentials.username,
        registry_credentials.passwords[0].value
    )
    pulumi.export("container_group_name", container_group.name)

# Create Logic App if enabled
if Config.enable_logic_app and Config.enable_container_instances:
    logic_app = create_logic_app(
        name=Config.get_resource_name("logicapp"),
        resource_group=rg,
        location=Config.location,
        container_group_id=container_group.id,
        subscription_id=Config.subscription_id
    )
    pulumi.export("logic_app_name", logic_app.name)

# Create Budget alerts if enabled
if Config.enable_budget:
    budget = create_budget(
        name=Config.get_resource_name("budget"),
        resource_group_name=rg.name,
        subscription_id=Config.subscription_id,
        owners=Config.rbacConfig["owners"],
        max_budget_amount=Config.max_budget_amount,
        increment=Config.budget_increment
    )

if Config.enable_local_env_variables:
    load_dotenv(dotenv_path="../src/.env")