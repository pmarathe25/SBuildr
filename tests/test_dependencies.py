from sbuildr.project.dependencies.fetchers.git_fetcher import GitFetcher

import tempfile
import pytest
import os

def test_can_fetch_stest_repo():
    commit_hash = "b2dd61e5669f9a2dee75d55eaf2950a722eebeae"
    fetcher = GitFetcher(url="https://github.com/pmarathe25/SLog.git", commit=commit_hash)

    with tempfile.TemporaryDirectory() as install_dir:
        dep_info = fetcher.fetch(install_dir)
        assert dep_info.name == "SLog"
        assert dep_info.path == os.path.join(install_dir, "SLog")
        assert dep_info.version_tags == [commit_hash]
        assert os.path.exists(dep_info.path)
