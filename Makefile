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
	python3 -m pytest tests/
	# TODO: Move this into test_integration.
	export PYTHONPATH=$(CURDIR); python3 examples/minimal_project/build.py && bin/sbuildr -p examples/minimal_project/project.sbuildr configure-backend -vv && bin/sbuildr -p examples/minimal_project/project.sbuildr build -vv && bin/sbuildr -p examples/minimal_project/project.sbuildr tests -vv

wheel:
	python3 setup.py bdist_wheel

install: wheel
	python3 -m pip install dist/*.whl --user --upgrade --force-reinstall

clean:
	-rm -r $(CURDIR)/build/ $(CURDIR)/dist/ $(CURDIR)/SBuildr.egg-info

upload: wheel
	python3 -m twine upload dist/*
