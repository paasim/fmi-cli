.PHONY: build check clean install run test upgrade

build:
	uv build --wheel

check: .git/hooks/pre-commit
	./$<

clean:
	rm -rf .venv *.egg-info build dist uv.lock

install:
	uv sync --frozen

run:
	uv run python

test:
	uv run pytest

upgrade:
	uv sync --upgrade

.git/hooks/pre-commit:
	curl -L https://gist.githubusercontent.com/paasim/8603fb8b849f4e9a0d0ece9ed9180751/raw/e57b5f19298ad682c88b34d791295471d2fd8661/python-pre-commit.sh > $@
	echo "" >> $@
	chmod +x $@
