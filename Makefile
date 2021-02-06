all: prod

.PHONY: requirements.txt
requirements.txt:
	poetry export -f requirements.txt --output requirements.txt

.PHONY: download_covers
download_covers:
	entry/scripts/download_yt_thumbnails.py

.PHONY: prod
prod:
	cd app && \
		node_modules/.bin/browserify src/main.js -o static/bundle.js -t [ babelify --presets [ @babel/preset-env ] ]

.PHONY: dev
dev:
	cd app && \
		node_modules/.bin/browserify src/main.js -o static/bundle.js -p esmify --debug

.PHONY: install
install:
	cd app && npm install

.PHONY: clean
clean:
	rm -f app/static/bundle.js