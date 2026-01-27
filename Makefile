# Makefile for Docker environment management
SHELL := /bin/bash
DC := docker compose

# Docker compose files
COMPOSE_PROD := docker-compose.yml
COMPOSE_DEV := docker-compose.local.yml

# OS detection and color configuration
ifeq ($(OS),Windows_NT)
	# Windows does not support ANSI color codes in standard Command Prompt
	GREEN :=
	NC :=
else
	GREEN := \033[0;32m
	NC := \033[0m # No Color
endif

.PHONY: start start-local down down-local ps clean

# Generic commands with compose file as parameter
define docker_up
	@echo "$(GREEN)Building and starting $(1) containers...$(NC)"
	$(DC) -f $(2) up --build -d
endef

define docker_down
	@echo "$(GREEN)Stopping $(1) containers...$(NC)"
	$(DC) -f $(2) down
endef

# Production commands
start:
	$(call docker_up,production,$(COMPOSE_PROD))

down:
	$(call docker_down,production,$(COMPOSE_PROD))

# Development commands
start-local:
	$(call docker_up,development,$(COMPOSE_DEV))

down-local:
	$(call docker_down,development,$(COMPOSE_DEV))

# Utility commands
ps:
	@echo "$(GREEN)Listing running containers...$(NC)"
	$(DC) ps

clean:
	@echo "$(GREEN)Removing all containers and images...$(NC)"
	$(DC) -f $(COMPOSE_PROD) down --rmi all --volumes --remove-orphans
	$(DC) -f $(COMPOSE_DEV) down --rmi all --volumes --remove-orphans 