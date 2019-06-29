# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

test:
	python -m pytest tests/
	export PYTHONPATH=$(CURDIR); python examples/minimal_project/build.py build && python examples/minimal_project/build.py tests

wheel:
	python setup.py bdist_wheel

install: wheel
	python -m pip install dist/*.whl --user --upgrade

clean:
	-rm -r $(CURDIR)/build/ $(CURDIR)/dist/ $(CURDIR)/SBuildr.egg-info

upload: wheel
	python -m twine upload dist/*
