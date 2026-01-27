import pulumi
from pulumi_azure_native import cognitiveservices


def create_openai_account(name: str, resource_group_name: pulumi.Output[str], location: str):
    account = cognitiveservices.Account("openAI_account",
                                        account_name=name,
                                        identity={
                                            "type": cognitiveservices.ResourceIdentityType.SYSTEM_ASSIGNED,
                                        },
                                        kind="OpenAI",
                                        location=location,
                                        resource_group_name=resource_group_name,
                                        sku={
                                            "name": "S0",
                                        })
    return account


def deploy_openai_model(name: str, resource_group_name: pulumi.Output[str], account_name: str):
    deployment = cognitiveservices.Deployment("openAI_deployment",
                                              account_name=account_name,
                                              deployment_name=name,
                                              properties={
                                                  "model": {
                                                      "format": "OpenAI",
                                                      "name": "gpt-4o",
                                                      "version": "2024-08-06",
                                                  },
                                              },
                                              resource_group_name=resource_group_name,
                                              sku={
                                                  "capacity": 50,  # Token rate limit of 1000 per unit
                                                  "name": "DataZoneStandard",
                                              })
    return deployment


def deploy_embedding_model(
    name: str, resource_group_name: pulumi.Output[str], account_name: str
):
    deployment = cognitiveservices.Deployment(
        "openAI_embedding_deployment",
        account_name=account_name,
        deployment_name=name,
        properties={
            "model": {
                "format": "OpenAI",
                "name": name,
                "version": "1",
            },
        },
        resource_group_name=resource_group_name,
        sku={
            "capacity": 100,  # Token rate limit of 1000 per unit
            "name": "Standard",
        },
    )
    return deployment