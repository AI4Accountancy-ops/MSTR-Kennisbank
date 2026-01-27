import pulumi
import pulumi_azure_native as azure

from environments.base import BaseConfig


def create_cosmos_db(name: str, resource_group_name: pulumi.Output[str], location: str):
    account = azure.documentdb.DatabaseAccount(
        name,
        account_name=name,
        resource_group_name=resource_group_name,
        location=location,
        database_account_offer_type=azure.documentdb.DatabaseAccountOfferType.STANDARD,
        locations=[azure.documentdb.LocationArgs(
            location_name=location,
            failover_priority=0
        )],
        consistency_policy=azure.documentdb.ConsistencyPolicyArgs(
            default_consistency_level=azure.documentdb.DefaultConsistencyLevel.SESSION,
        ),
    )
    return account


def create_database(cosmos_db_name: BaseConfig, cosmos_db: azure.documentdb.DatabaseAccount, rg: azure.resources.ResourceGroup):
    return azure.documentdb.SqlResourceSqlDatabase(
        resource_name=cosmos_db_name,
        account_name=cosmos_db.name,
        resource_group_name=rg.name,
        resource=azure.documentdb.SqlDatabaseResourceArgs(
            id=cosmos_db_name,
        ),
        opts=pulumi.ResourceOptions(depends_on=[cosmos_db])
    )


def create_container(container_name: str, cosmos_db: azure.documentdb.DatabaseAccount,
                     database: azure.documentdb.SqlResourceSqlDatabase, rg: azure.resources.ResourceGroup):
    return azure.documentdb.SqlResourceSqlContainer(
        resource_name=container_name,
        account_name=cosmos_db.name,
        database_name=database.name,
        resource_group_name=rg.name,
        resource=azure.documentdb.SqlContainerResourceArgs(
            id=container_name,
            partition_key=azure.documentdb.ContainerPartitionKeyArgs(
                paths=["/id"],
                kind="Hash",
            ),
            indexing_policy=azure.documentdb.IndexingPolicyArgs(
                indexing_mode="consistent",
                automatic=True,
                included_paths=[
                    azure.documentdb.IncludedPathArgs(
                        path="/*",
                    ),
                ],
                excluded_paths=[],
            ),
        ),
        options=azure.documentdb.CreateUpdateOptionsArgs(
            throughput=400  # Adjust as needed
        ),
        opts=pulumi.ResourceOptions(depends_on=[database])
    )


def get_cosmos_db_connection_string(account_name: pulumi.Input[str], resource_group_name: pulumi.Input[str]):
    keys = azure.documentdb.list_database_account_keys_output(
        account_name=account_name,
        resource_group_name=resource_group_name
    )
    return pulumi.Output.all(account_name, keys).apply(lambda args:
        f"AccountEndpoint=https://{args[0]}.documents.azure.com:443/;AccountKey={args[1].primary_master_key};"
    )
