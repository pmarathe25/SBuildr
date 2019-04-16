from srbuild.project.project import Project
from srbuild.logger import G_LOGGER
from test_tools import PATHS, ROOT
import glob
import os

G_LOGGER.severity = G_LOGGER.VERBOSE

class TestProject(object):
    def test_project_inits_to_curdir(self):
        proj = Project()
        assert proj.root_dir == os.path.dirname(__file__)

    def test_project_globs_files(self):
        proj = Project(dirs=[os.path.relpath(os.path.join(os.path.dirname(__file__), "minimal_project"))])
        all_files = []
        for file in glob.iglob(os.path.join(ROOT, "**"), recursive=True):
            if os.path.isfile(file):
                all_files.append(os.path.abspath(file))
        assert proj.files == all_files
        assert all([os.path.isabs(file) for file in proj.files])

    def test_project_find(self):
        proj = Project(root=ROOT)
        for filename, path in PATHS.items():
            if os.path.isfile(path):
                assert proj.find(filename) == [path]
