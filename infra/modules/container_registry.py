import pulumi
import pulumi_docker_build as docker_build
from pulumi_azure_native import containerregistry


def create_container_registry(name: str, resource_group_name: pulumi.Output[str], location: str):
    registry = containerregistry.Registry(
        name,
        registry_name=name,
        resource_group_name=resource_group_name,
        location=location,
        sku=containerregistry.SkuArgs(
            name="Basic",
        ),
        admin_user_enabled=True,
    )
    return registry


def get_registry_credentials(registry_name: str, resource_group_name: pulumi.Output[str]):
    return containerregistry.list_registry_credentials_output(
        registry_name=registry_name,
        resource_group_name=resource_group_name
    )


def push_docker_image(
    container_registry: containerregistry.Registry,
    registry_credentials_output: pulumi.Output[containerregistry.ListRegistryCredentialsResult],
    image_name: str,
    image_tag: str,
    context_path: str,
    docker_file_path: str,
    environment: str = "dev"
):
    # Ensure image_name and image_tag are lowercase
    image_name_lower = image_name.lower()
    image_tag_lower = image_tag.lower()

    # Define a function to create the Docker image
    def create_docker_image(args):
        login_server, username, passwords = args
        password = passwords[0]['value']

        # Construct the full image name
        full_image_name = f"{login_server}/{image_name_lower}:{image_tag_lower}"

        # Create the registry credentials
        registry_args = docker_build.RegistryArgs(
            address=login_server,
            username=username,
            password=password
        )

        # Build and push the image
        image = docker_build.Image(
            image_name_lower,
            tags=[full_image_name],
            context=docker_build.BuildContextArgs(
                location=context_path,
            ),
            platforms=[
                docker_build.Platform.LINUX_AMD64,
            ],
            dockerfile=docker_build.DockerfileArgs(
                location=docker_file_path,
            ),
            build_args={
                "ENVIRONMENT": environment,
            },
            push=True,
            registries=[registry_args],
        )

        return image

    # Use pulumi.Output.all() to handle asynchronous values
    docker_image = pulumi.Output.all(
        container_registry.login_server,
        registry_credentials_output.username,
        registry_credentials_output.passwords
    ).apply(create_docker_image)

    return docker_image