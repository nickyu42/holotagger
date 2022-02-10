all: prod

.PHONY: requirements.txt
requirements.txt:
	poetry export -f requirements.txt --output requirements.txt

.PHONY: download_covers
download_covers:
	entry/scripts/download_yt_thumbnails.py

.PHONY: prod
prod:
	cd app && npm run prod

.PHONY: dev
dev:
	cd app && npm run dev

.PHONY: install
install:
	cd app && npm install

.PHONY: lint
lint:
	poetry run flake8 --ignore E501 src

.PHONY: clean
clean:
	rm -f app/static/bundle.js