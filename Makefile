APP_NAME = climgrid
PIP = ./env/bin/pip3
PY = ./env/bin/python3

##################################
# Local development commands
##################################

install:
	${PIP} install -r requirements.txt

clean:
	rm -rf .eggs/ build/ dist/ logs/ *.egg-info/ .tox/
	-find . -name '__pycache__' -prune -exec rm -rf "{}" \;
	-find . -name '*.py[co]' -delete

lint:
	./env/bin/flake8 ${APP_NAME}.py

format:
	./env/bin/yapf -r -i ${APP_NAME}.py

workers:
	./env/bin/celery multi start 4 -c 20 --autoscale=15,4 -A ${APP_NAME} -l info --logfile=./celery.log

workers-stop:
	./env/bin/celery multi stopwait 4 -A ${APP_NAME} -l info

run:
	time ${PY} ${APP_NAME}.py

DB_NAME='precipitation'
DB_USER='climgrid'
create-db-user:
	sudo -u postgres -c 'CREATE DATABASE ${DB_NAME};'
	psql -U postgres -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_USER}';"
	psql -U postgres -c 'GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};'

# start a cloud sql proxy
cloud-proxy:
	 cloud_sql_proxy -instances=${INSTANCE_CONNECTION_NAME}=tcp:5432 -credential_file=${CREDS_FILE}

# open up psql by pointing to cloud sql proxy
cloud-psql:
	psql "host=127.0.0.1 sslmode=disable dbname=${DB_NAME} user=${DB_USER}"

CI_BUILD_REF ?= $(shell git rev-parse --verify HEAD)
CONTAINER_REGISTRY ?= localhost:4444
CONTAINER_NAME_BASE = ${CONTAINER_REGISTRY}/${APP_NAME}

##################################
# Docker container management
##################################

docker-build:
	docker build \
		-t ${CONTAINER_NAME_BASE}:${CI_BUILD_REF} \
		-t ${CONTAINER_NAME_BASE}:latest \
		--build-arg "commit=${CI_BUILD_REF}" \
		.

docker-publish:
	docker push ${CONTAINER_NAME_BASE}:${CI_BUILD_REF}
	docker push ${CONTAINER_NAME_BASE}:latest

docker-run:
	docker run -it --rm ${CONTAINER_NAME_BASE}:${CI_BUILD_REF} /bin/bash

###################################
# Helm/Kubernetes commands
##################################

CI_BUILD_SHORT_REF ?= $(shell git rev-parse --short HEAD)
ENVIRONMENT ?= development
RELEASE_NAME = ${APP_NAME}-${CI_BUILD_SHORT_REF}

gcloud-publish:
	gcloud docker -- push ${CONTAINER_NAME_BASE}:${CI_BUILD_REF}
	gcloud docker -- push ${CONTAINER_NAME_BASE}:latest

helm-install:
	helm install \
	  --name=${RELEASE_NAME}\
		--namespace=${APP_NAME} \
		--set commit=${CI_BUILD_REF} \
		--set image.tag=${CI_BUILD_REF} \
		--set image.registry=${CONTAINER_REGISTRY} \
		--set redis.fullnameOverride=${APP_NAME}-redis-${CI_BUILD_REF} \
		./ops/charts/${APP_NAME}

helm-upgrade:
	helm upgrade ${RELEASE_NAME} \
		--namespace=${APP_NAME} \
		--recreate-pods \
		--set commit=${CI_BUILD_REF} \
		--set image.tag=${CI_BUILD_REF} \
		--set image.registry=${CONTAINER_REGISTRY} \
		--set redis.fullnameOverride=${APP_NAME}-redis-${CI_BUILD_REF} \
		./ops/charts/${APP_NAME}

helm-drop-all:
	helm ls | tail -n+2 | awk '{print $$1}' | xargs helm delete --purge

helm-status:
	helm status ${RELEASE_NAME}

helm-delete:
	helm delete --purge ${RELEASE_NAME}
