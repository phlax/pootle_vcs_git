from git import Repo

from pootle_vcs import Plugin, plugins


class GitPlugin(Plugin):
    name = "git"

    @property
    def repo(self):
        return Repo(self.local_repo_path)

    def pull(self):
        if not self.is_cloned:
            Repo.clone_from(self.vcs.url, self.local_repo_path)
        self.repo.remote().pull()

    def get_latest_commit(self):
        self.pull()
        return self.repo.commit().hexsha

plugins.register(GitPlugin)
