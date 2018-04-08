workers:
	./env/bin/celery multi start w1 -A pd_convert -l info --logfile=./celery.log

workers-stop:
	./env/bin/celery multi stopwait w1 -A pd_convert -l info

run:
	time ./env/bin/python3 pd_convert.py

DB_NAME='precipitation'
DB_USER='climgrid'
create-db-user:
	sudo -u postgres -c 'CREATE DATABASE ${DB_NAME};'
	psql -U postgres -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_USER}';"
	psql -U postgres -c 'GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};'
