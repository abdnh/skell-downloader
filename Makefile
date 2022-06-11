.PHONY: all fix mypy pylint
all: fix mypy pylint

fix:
	python -m black .
	python -m isort .

mypy:
	python -m mypy .

pylint:
	python -m pylint skell_downloader.py
