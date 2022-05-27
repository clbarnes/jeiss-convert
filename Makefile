.PHONY: fmt
fmt:
	isort . \
	&& black .

.PHONY: lint
lint:
	black --check .
	isort --check .
	flake8 .

lint-type: lint
	mypy .

.PHONY: test
test:
	pytest --verbose

.PHONY: install
install:
	pip install .

.PHONY: install-dev
install-dev:
	pip install -r requirements.txt \
	&& pip install -e .

.PHONY: clean-docs
clean-docs:
	rm -rf docs

.PHONY: docs
docs: clean-docs
	mkdir -p docs \
	&& pdoc --html --output-dir docs jeiss-convert

.PHONY: readme
readme:
	dat2hdf5 --help | p2c --tgt _dat2hdf5 README.md
	dat2hdf5-verify --help | p2c --tgt _dat2hdf5-verify README.md
