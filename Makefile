# setting the PATH seems only to work in GNUmake not in BSDmake
PATH:=pythonenv/bin:$(PATH)

default: dependencies

dependencies:
	virtualenv pythonenv
	pip -q install -E pythonenv -r requirements.txt

upload: build
	python setup.py sdist upload

.PHONY: dependencies upload
