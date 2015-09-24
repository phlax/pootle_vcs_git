from glob import glob
import io
from itertools import chain
import os
from ConfigParser import ConfigParser

from git import Repo

from pootle_language.models import Language
from pootle_translationproject.models import TranslationProject

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
        self.repo.remote().pull()

    def get_latest_commit(self):
        self.pull()
        return self.repo.commit().hexsha

    def find_translation_files(self):
        config = self.read_config()
        translation_path = os.path.join(self.local_repo_path,
                                        config.get("pootle", "translation_path"))
        # todo: add mapping of exts/project_type somewhere
        return (chain.from_iterable(glob(os.path.join(x[0], '*.po'))
                                    for x in os.walk(translation_path)))

    def pull_translation_files(self):
        for f in self.find_translation_files():
            path, ext = os.path.splitext(f)
            lang = Language.objects.get(code=os.path.basename(path))
            try:
                tp = self.vcs.project.translationproject_set.get(language=lang)
            except TranslationProject.DoesNotExist:                
                import pdb; pdb.set_trace()

    def read(self, path):
        target = os.path.join(self.local_repo_path, path)
        with open(target) as f:
            content = f.read()
        return content

    def read_config(self):
        self.pull()
        config = ConfigParser()
        config.readfp(io.BytesIO(self.read(self.vcs.pootle_config)))
        return config


plugins.register(GitPlugin)
