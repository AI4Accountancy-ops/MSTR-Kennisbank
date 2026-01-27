container_registry_template = """
name: Docker Build {env}

on:
  push:
    branches:
      - {env}

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v2

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v1

    - name: Login to Azure Container Registry
      uses: azure/docker-login@v1
      with:
        login-server: ${{{{ secrets.ACR_LOGIN_SERVER_{env} }}}}
        username: ${{{{ secrets.ACR_USERNAME_{env} }}}}
        password: ${{{{ secrets.ACR_PASSWORD_{env} }}}}

    - name: Build and push Docker image
      uses: docker/build-push-action@v2
      with:
        context: .
        push: true
        tags: {url_to_image}
"""