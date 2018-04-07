workers:
	./env/bin/celery multi start w1 -A pd_convert -l info --logfile=./celery.log

workers-stop:
	./env/bin/celery multi stopwait w1 -A pd_convert -l info

run:
	time ./env/bin/python3 pd_convert.py
