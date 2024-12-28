
# UpWorkSpider

**UpWorkSpider** is a project using Scrapy and Playwright to automate data collection from the Escore and HLTV websites. This guide outlines the steps for installing dependencies, setting up the environment, and running the project.

## Contents

- [Installation](#installation)
  - [Install Playwright and Browsers](#install-playwright-and-browsers)
  - [Resolving "Permission Denied" Errors](#resolving-permission-denied-errors)
- [Usage](#usage)
  - [Launching the Scrapyd Server](#launching-the-scrapyd-server)
  - [Scheduling the Spider](#scheduling-the-spider)
- [Makefile](#makefile)
  - [Available Commands](#available-commands)
## Local Installation

### .env File example
``` bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=fluxbackendwsl
DB_USER=postgres
DB_PASS=postgres
DB_URL=postgres://postgres:postgres@localhost:5432/fluxbackendwsl
```

### Install Playwright and Browsers

To ensure Playwright works correctly, you need to install Playwright itself and the corresponding browsers. Execute the following commands:

```bash
poetry install
poetry run playwright install --with-deps chromium
```
### Resolving "Permission Denied" Errors

When installing or running Playwright on UNIX-based systems (Linux, macOS), you might encounter "Permission denied" errors for certain files. To resolve this issue, you need to set execute permissions for the relevant files.

#### Steps to Resolve: (Local)

1. **Identify the Path to the Problematic Files.** Typically, they look like this:
```bash
/usr/local/lib/python3.12/site-packages/undetected_playwright/driver/playwright.sh
/usr/local/lib/python3.12/site-packages/undetected_playwright/driver/node
```

2. **Set Execute Permissions:**
```bash
chmod +x /usr/local/lib/python3.12/site-packages/undetected_playwright/driver/playwright.sh
chmod +x /usr/local/lib/python3.12/site-packages/undetected_playwright/driver/node
``` 

   **Note:** You might need to use `sudo` to gain the necessary permissions:
```bash
sudo chmod +x /usr/local/lib/python3.12/site-packages/undetected_playwright/driver/playwright.sh
sudo chmod +x /usr/local/lib/python3.12/site-packages/undetected_playwright/driver/node
```

## Container usage

### .env File Example
```bash
DB_HOST=host.docker.internal
DB_PORT=5432
DB_NAME=fluxbackendwsl
DB_USER=postgres
DB_PASS=postgres
DB_URL=postgres://postgres:postgres@host.docker.internal:5432/fluxbackendwsl
```

### Launching the Scrapyd Server

To launch the Scrapyd server, use Docker Compose. Ensure you have Docker and Docker Compose installed on your system.

**Start the Scrapyd Server:**

```bash
docker compose up
```

This command starts the containers required for Scrapyd, including the server and the database.

### Scheduling the Spider

After launching the Scrapyd server, you can schedule the spider to run using the `schedule_*.py` script.

**Run the Scheduling Script:**

```bash
python3 src/schedule_*.py
```
This script sends a request to the Scrapyd server to start the specified spider.

Scrapyd server info will be present at
```bash
http://localhost:6800/
```

## Makefile

The `Makefile` contains convenient commands for managing the project, such as installing dependencies, linting the code, formatting the code, and running tests.

### Available Commands

All commands are described in the `Makefile` with corresponding explanations. To view the list of available commands, use the `make help` command.

```makefile
SOURCES := $(shell find . -name '*.py')

.DEFAULT_GOAL := help
.PY = poetry run

help: ## Display this help screen
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
.PHONY: help

install: ## Install project dependencies
	poetry install --with dev --no-interaction --no-ansi --no-root
.PHONY: install

lint: ## Lint the source code
	$(.PY) ruff check --config pyproject.toml --no-fix $(SOURCES)
.PHONY: lint

format: ## Format the source code
	$(.PY) ruff check --config pyproject.toml --fix $(SOURCES)
	$(.PY) ruff format --config pyproject.toml $(SOURCES)
.PHONY: format

test: ## Run the test suite
	$(.PY) pytest
.PHONY: test
```

#### Command Descriptions:

- **help:** Displays the list of available commands with descriptions.

  ```bash
  make help
  ```

- **install:** Installs all project dependencies, including development dependencies.

  ```bash
  make install
  ```

- **lint:** Checks the source code for compliance with coding standards using `ruff`.

  ```bash
  make lint
  ```

- **format:** Formats the source code and fixes any detected issues.

  ```bash
  make format
  ```

- **test:** Runs the test suite using `pytest`.

  ```bash
  make test
  ```
