.PHONY: install run dev test lint infra-install infra-deploy infra-destroy infra-diff \
        docker-build docker-run docker-stop docker-logs docker-push docker-deploy

IMAGE_NAME  = lemon-api
IMAGE_TAG   ?= latest
ECR_REPO    ?= 375243950000.dkr.ecr.us-east-1.amazonaws.com/$(IMAGE_NAME)

VENV     = .venv
PYTHON   = $(VENV)/bin/python
PIP      = $(VENV)/bin/pip
UVICORN  = $(VENV)/bin/uvicorn
PYTEST   = $(VENV)/bin/pytest

# ── Python App ─────────────────────────────────────────────────────────────

venv:
	python3 -m venv $(VENV)

install: venv
	$(PIP) install --upgrade pip --quiet
	$(PIP) install -r requirements.txt

run:
	$(PYTHON) run.py

dev:
	DEBUG=true $(UVICORN) app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	$(PYTEST) tests/ -v

lint:
	$(VENV)/bin/ruff check app/ && $(VENV)/bin/mypy app/

# ── Manual job triggers (dev/testing) ─────────────────────────────────────

trigger-daily-summary:
	curl -s -X POST "http://localhost:8000/api/v1/jobs/daily-summary?userId=$(userId)" | jq .

trigger-sprint-summary:
	curl -s -X POST "http://localhost:8000/api/v1/jobs/sprint-summary?userId=$(userId)&sprintId=$(sprintId)" | jq .

trigger-roadmap-summary:
	curl -s -X POST "http://localhost:8000/api/v1/jobs/roadmap-summary?sprintId=$(sprintId)" | jq .

trigger-ingestion:
	curl -s -X POST "http://localhost:8000/api/v1/ingestion/trigger" \
		-H "Content-Type: application/json" \
		-d '{"source":"taskei","user_id":"$(userId)"}' | jq .

# ── CDK Infrastructure ─────────────────────────────────────────────────────

infra-install:
	cd infra && npm install

infra-diff:
	cd infra && npx cdk diff

infra-deploy:
	cd infra && npx cdk deploy --all --require-approval never

infra-destroy:
	cd infra && npx cdk destroy --all

# ── Docker ─────────────────────────────────────────────────────────────────

## Build the Docker image locally
docker-build:
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .

## Run the container locally (uses host AWS credentials)
docker-run:
	docker compose up -d
	@echo "API running at http://localhost:8000"
	@echo "Docs at      http://localhost:8000/docs"

## Stop the container
docker-stop:
	docker compose down

## Tail container logs
docker-logs:
	docker compose logs -f api

## Login to ECR, tag, and push image
docker-push: docker-build
	aws ecr get-login-password --region us-east-1 | \
		docker login --username AWS --password-stdin 375243950000.dkr.ecr.us-east-1.amazonaws.com
	docker tag $(IMAGE_NAME):$(IMAGE_TAG) $(ECR_REPO):$(IMAGE_TAG)
	docker push $(ECR_REPO):$(IMAGE_TAG)
	@echo "Pushed $(ECR_REPO):$(IMAGE_TAG)"

## SSH into EC2 via SSM and pull + restart the container
docker-deploy:
	@echo "Deploying to EC2 via SSM..."
	aws ssm send-command \
		--region us-east-1 \
		--instance-ids i-0c98f7b176b6725e3 \
		--document-name "AWS-RunShellScript" \
		--parameters 'commands=["cd /opt/lemon && docker compose pull && docker compose up -d --force-recreate"]' \
		--output text \
		--no-cli-pager
	@echo "Deploy command sent. Check SSM Run Command in AWS Console for status."
