import os

from git import Repo

from pootle_vcs import Plugin, plugins


class GitPlugin(Plugin):
    name = "git"

    def __init__(self, vcs):
        self.vcs = vcs

    @property
    def local_repo_path(self):
        vcs_path = "/tmp"
        return os.path.join(vcs_path, self.vcs.project.code)

    @property
    def repo(self):
        return Repo(self.local_repo_path)

    @property
    def is_cloned(self):
        if os.path.exists(self.local_repo_path):
            return True
        return False

    def pull(self):
        if not self.is_cloned:
            Repo.clone_from(self.vcs.url, self.local_repo_path)

    def get_latest_commit(self):
        self.pull()
        return self.repo.commit().hexsha

    def pull_translation_files(self):
        pass


plugins.register(GitPlugin)
