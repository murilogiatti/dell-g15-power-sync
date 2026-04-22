.PHONY: install uninstall update

install:
	./install.sh

uninstall:
	./uninstall.sh

update:
	git pull
	./install.sh
