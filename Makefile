test:
	python -m pytest tests/
	python tests/minimal_project/build.py configure && python tests/minimal_project/build.py build

wheel:
	python setup.py bdist_wheel

install: wheel
	python -m pip install dist/*.whl --user --upgrade

clean:
	-rm -r $(CURDIR)/build/ $(CURDIR)/dist/ $(CURDIR)/SBuildR.egg-info

upload: wheel
	python -m twine upload dist/*
