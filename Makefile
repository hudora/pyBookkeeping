# we assume this redisdes in a hierachy created by silver-build-layout.sh
# setting the PATH seems only to work in GNUmake not in BSDmake
PATH := ../../bin:$(PATH)
SILVERNODE := mischosting
PROJECTDNS := %%PROJECTNAME%%.hudora.biz

runserver:
	silver serve ../..

deploy:
	silver update --host $(PROJECTDNS) --node $(SILVERNODE) ../..

firstdeploy:
	# make SURE all dependencis are in the virtualenv
	../../bin/pip install -I -r ./requirements.txt
	silver -v update --host $(PROJECTDNS) --node $(SILVERNODE) ../..
	(cd ../../; silver run $(SILVERNODE) manage.py syncdb --noinput)

livedb_to_test:
	# copies database from the live system onto your box
	scp root@$(PROJECTDNS):/var/lib/silverlining/apps/%%PROJECTNAME%%/%%MODULENAME%%.db ~/.silverlining-app-data/files/%%PROJECTNAME%%/%%MODULENAME%%.db

setup: dependencies
	../../bin/python ../../bin/manage.py syncdb --noinput

dependencies: update_templates
	../../bin/pip -q install -r ./requirements.txt

update_templates: generic_templates
	cd html ; git pull ; cd -
	
generic_templates:
	git clone git@github.com:hudora/html.git html
	ln -s html/templates generic_templates
			
clean:
	find . -name '*.pyc' -or -name '*.pyo' | xargs rm

test:
	python manage.py test --verbosity=1 %%MODULENAME%%
