## Setup the infra 

*Prerequisites*

- An azure `subscription_id`
- An azure `tenant_id`
- A `github_pat` (See [Create a GITHUB_PAT](#create-a-github_pat) on how to create one.)
- An Pulumi account (*For a pulumi access token: https://www.pulumi.com*) 
- Docker running locally

Add all the variables to the `.env` file. like in the `env_example` file.

- INTERNAL-API-KEY = 
- CLIENT_URL =

## Fill the BaseConfig in the infra/environments/base.py with the correct variables.

Add the following 3 values to the BaseConfig in the `base.py` file: `subscription_id`, `tenant_id` and `github_pat`
the rest of the variables are already set.

## Add owners to the Config

Add the correct owners (azure resource group owners) to the `development.py`, `staging.py` and `production.py` files.

This should be the **User principal name** of the user who is the owner of the Azure resource group.

*example*
```
rbacConfig = {
    "owners": ["<user_email>#EXT#@<username>.onmicrosoft.com"],
    "contributors": [],
    "readers": []
}
```

## Create a GITHUB_PAT
If you already have a personal access token you can skip this part.

1. Go to: https://github.com/settings/personal-access-tokens/new and create a new (classic) token.
2. Under `Select scopes` check the following options
   - codespace
   - admin:repo_hook
   - workflow

Finally, generate the token

***Note*: make sure PAT's (personal access tokens) are enabled within your org**

## Make sure you're in the correct subscription (Pulumi will create in this subscription)
Install azure-cli if not installed:
```bash
brew update && brew install azure-cli
```

```bash
az account show --query name
```

if not then switch:
```bash
az account set --subscription "Subscription Name or ID"
```

## Install pulumi if not installed
```bash
brew install pulumi (on mac)
pulumi plugin install resource azure-native v2.0.0
```

## Pip install dev requirements
```bash
pip install -r infra/requirements.txt
```

## Login to pulumi
```bash
pulumi login
```

## Navigate to the infra directory
```bash
cd infra
```

## Init pulumi stack
Make sure the project name is correctly specified in the pulumi.yaml file.
```bash
pulumi stack init mstr/<project_name>/<env-name> (dev or production for example)
```

## Switch between stack
```bash
pulumi stack select <stack-name>
```

**Depending on the virtual environment you are using, add the correct venv path after `virtualenv:` to the Pulumi.yaml file**

*For the following steps, make sure you have docker installed and running locally*

## Deploy pulumi stack
```bash
pulumi up
```

## Do you want to perform this update?
When you run `pulumi up` you will be prompted to confirm the update.
Choose `yes` if you want to update the stack.
```bash
yes
```

## In case you manually remove something:
```bash
pulumi refresh
```