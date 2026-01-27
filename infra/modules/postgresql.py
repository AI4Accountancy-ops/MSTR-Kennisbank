from pulumi_azure_native import dbforpostgresql
from pulumi_random import RandomPassword
from pulumi import Output


def create_postgresql_server(name: str, resource_group_name: Output[str], location: str):
    # Generate a secure password
    password = RandomPassword(
        f"{name}-admin-password",
        length=16,
        special=True,
        override_special="_@",
    )

    server = dbforpostgresql.Server(
        resource_name=f"{name}",
        server_name=name,
        resource_group_name=resource_group_name,
        location=location,
        sku=dbforpostgresql.SkuArgs(
            name="Standard_B1ms",
            tier="Burstable",  # More general puprose like development and testing, not needed continous operations
        ),
        storage=dbforpostgresql.StorageArgs(
            storage_size_gb=32,  # Minimum storage size for Burstable tier
        ),
        administrator_login="postgresadmin",
        administrator_login_password=password.result,
        create_mode="Default",
    )

    # Enable pgvector and vectorscale extensions
    dbforpostgresql.Configuration(
        resource_name=f"{name}-config-extensions",
        resource_group_name=resource_group_name,
        server_name=server.name,
        configuration_name="azure.extensions",
        value="vector",
        source="user-override",
    )

    # **Add a firewall rule to allow all IP addresses**
    dbforpostgresql.FirewallRule(
        resource_name=f"{name}-allow-all",
        resource_group_name=resource_group_name,
        server_name=server.name,
        start_ip_address="0.0.0.0",
        end_ip_address="255.255.255.255",
    )

    return server, password.result


def get_postgresql_connection_string(server_fqdn: Output[str], admin_username: str, admin_password: Output[str]) -> Output[str]:
    return Output.concat(
        "postgresql://",
        admin_username,
        ":",
        admin_password,
        "@",
        server_fqdn,
        ":5432/postgres?sslmode=require",
    )