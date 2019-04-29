#!/usr/bin/env zsh
python -m pytest tests/ "$@"
python tests/minimal_project/build.py configure && python tests/minimal_project/build.py build
