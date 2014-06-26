run:
	python -m server --logging=debug

clean:
	find . -type f -name '*.pyc' -delete -print

test:
	python -m unittest discover tests '*.py'

bootstap:
	./scripts/get_schema.py | mysql -uroot -D cirqle
