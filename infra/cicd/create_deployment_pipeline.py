import os

from github import Github

from cicd.templates.container_registry_github_actions import container_registry_template


def create_deployment_pipeline(pipeline_name: str, template_name: str, **kwargs):
    workflow_dir = "../.github/workflows"
    path = f"{workflow_dir}/{pipeline_name}.yml"
    os.makedirs(workflow_dir, exist_ok=True)

    if template_name == "container_registry":
        template = container_registry_template.format(**kwargs)
    else:
        raise ValueError(f"Template {template_name} not found")
    with open(path, "w") as f:
        f.write(template)


def add_secrets_to_github(github_pat: str, github_repo_name: str, secrets: dict):
    """
    Adds secrets to a GitHub repository
    :param github_pat: GitHub Personal Access Token
    :param github_repo_name: GitHub repository name
    :param secrets: Dictionary of secrets to add
    """
    # Replace with your PAT
    g = Github(github_pat)

    # Get the authenticated user
    repo = g.get_repo(github_repo_name) # make sure PAT's are enabled within your org

    for secret_name, secret_value in secrets.items():
        repo.create_secret(
            secret_name,
            secret_value,
        )


