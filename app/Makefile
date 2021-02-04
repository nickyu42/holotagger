all: build_web

.PHONY: build_web
build_web:
	./node_modules/.bin/browserify src/main.js -o static/bundle.js -t [ babelify --presets [ @babel/preset-env ] ]

.PHONY: build_dev
build_dev:
	./node_modules/.bin/browserify src/main.js -o static/bundle.js -p esmify --debug

.PHONY: install
install:
	npm install

.PHONY: clean
clean:
	rm -f web/bundle.js