all:
	python bot.py
beauty:
	black .
	isort .
	autoflake -r --remove-all-unused-imports .
install-beautifier:
	pip install black isort autoflake
