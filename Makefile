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
	export PYTHONPATH=$(CURDIR); python3 -m pytest tests/
	# TODO: Move these into separate tests.
	export PYTHONPATH=$(CURDIR); bin/sbuildr -p examples/minimal_project/build/project.sbuildr configure -b examples/minimal_project/build.py -vv && \
		bin/sbuildr -p examples/minimal_project/build/project.sbuildr build -vv && \
		bin/sbuildr -p examples/minimal_project/build/project.sbuildr test -vv && \
		bin/sbuildr -p examples/minimal_project/build/project.sbuildr clean --nuke --force; \
	export PYTHONPATH=$(CURDIR); bin/sbuildr -p examples/single_dependency/build/project.sbuildr configure -b examples/single_dependency/build.py -vv && \
		bin/sbuildr -p examples/single_dependency/build/project.sbuildr build -vv && \
		bin/sbuildr -p examples/single_dependency/build/project.sbuildr test -vv && \
		bin/sbuildr -p examples/single_dependency/build/project.sbuildr clean --nuke --force; \
		rm -r ~/.sbuildr/*/minimal_project*
	export PYTHONPATH=$(CURDIR); bin/sbuildr -p examples/nested_dependency/build/project.sbuildr configure -b examples/nested_dependency/build.py -vv && \
		bin/sbuildr -p examples/nested_dependency/build/project.sbuildr build -vv && \
		bin/sbuildr -p examples/nested_dependency/build/project.sbuildr test -vv && \
		bin/sbuildr -p examples/nested_dependency/build/project.sbuildr clean --nuke --force; \
		rm -r ~/.sbuildr/*/minimal_project* ~/.sbuildr/*/single_dependency*

clean:
	-rm -r $(CURDIR)/build/ $(CURDIR)/dist/ $(CURDIR)/SBuildr.egg-info

wheel: clean
	python3 setup.py bdist_wheel

install: wheel
	python3 -m pip install dist/*.whl --user --upgrade --force-reinstall

upload: wheel
	python3 -m twine upload dist/*
