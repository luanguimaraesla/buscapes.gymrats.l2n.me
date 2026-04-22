.PHONY: run data build clean

run: data
	hugo server --buildDrafts --disableFastRender

data:
	python3 scripts/process_data.py

build: data
	hugo --minify

clean:
	rm -rf public data
