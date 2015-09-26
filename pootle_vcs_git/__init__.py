from git import Repo

from pootle_vcs import Plugin, plugins, RepositoryFile


class GitRepositoryFile(RepositoryFile):

    @property
    def repo(self):
        return self.vcs.plugin.repo

    @property
    def latest_commit(self):
        return self.repo.git.log(
            '-1',
            '--pretty=%H',
            '--follow',
            '--',
            self.path)


class GitPlugin(Plugin):
    name = "git"
    file_class = GitRepositoryFile

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
