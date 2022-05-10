all:
	python bot.py
beauty:
	black .
	isort .
	autoflake -r --remove-all-unused-imports --in-place .
install-beautifier:
	pip install black isort autoflake
