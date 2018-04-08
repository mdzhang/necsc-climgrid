workers:
	./env/bin/celery multi start 4 -c 20 --autoscale=15,4 -A pd_convert -l info --logfile=./celery.log

workers-stop:
	./env/bin/celery multi stopwait 4 -A pd_convert -l info

run:
	time ./env/bin/python3 pd_convert.py

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
