from glob import glob
import io
from itertools import chain
import logging
import os
import re
from ConfigParser import ConfigParser

from git import Repo

from import_export.utils import import_file

from pootle_language.models import Language
from pootle_store.models import Store
from pootle_translationproject.models import TranslationProject

from pootle_vcs import Plugin, plugins


logger = logging.getLogger(__name__)


class RepoFile(object):

    pass


class GitRepoFile(RepoFile):

    def __init__(self, path, vcs, language, filename, directory_path=[]):
        self.vcs = vcs
        self.language = Language.objects.get(code=language)
        self.filename = filename
        self.directory_path = '/'.join(directory_path)
        self.path = path

    @property
    def project(self):
        return self.vcs.project

    @property
    def translation_project(self):
        return self.project.translationproject_set.get(language=self.language)

    @property
    def pootle_path(self):
        return "/".join(['']
                        + [x for x in [self.language.code,
                                       self.project.code,
                                       self.directory_path,
                                       self.filename]
                           if x])

    def __str__(self):
        return "<GitRepoFile: %s>" % self.pootle_path

    def read(self):
        # self.vcs.pull()
        with open(self.path) as f:
            return f.read()

    def sync(self):
        try:
            tp = self.translation_project
        except TranslationProject.DoesNotExist:
            tp = TranslationProject.objects.create(project=self.vcs.project,
                                                   language=self.language)

        directory = self.translation_project.directory
        if self.directory_path:
            for subdir in self.directory_path.split("/"):
                directory, created = directory.child_dirs.get_or_create(name=subdir)

        with open(self.path) as f:
            store, created = Store.objects.get_or_create(
                parent=directory, translation_project=tp, name=self.filename)
            if created:
                store.save()
            import_file(f, pootle_path=self.pootle_path, rev=store.get_max_unit_revision())


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

        for section in config.sections():
            translation_path = os.path.join(self.local_repo_path,
                                            config.get(section, "translation_path"))
            file_root = translation_path.split("<")[0]
            if not file_root.endswith("/"):
                file_root = "/".join(file_root.split("/")[:-1])

            match = (translation_path.replace(".", "\.")
                                     .replace("<lang>", "(?P<lang>[\w]*)")
                                     .replace("<filename>", "(?P<filename>[\w]*)")
                                     .replace("<directory_path>", "(?P<directory_path>[\w\/]*)"))

            match = re.compile(match)
            if section == "default":
                section_subdirs = []
            else:
                section_subdirs = section.split("/")
            # TODO: make sure translation_path has no ..
            for root, dirs, files in os.walk(file_root):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    matches = match.match(file_path)
                    subdirs = section_subdirs + [
                        m for m in 
                        matches.groupdict().get('directory_path', '').strip("/").split("/")
                        if m]
                    if matches:                        
                        # TODO: extension matching?
                        lang_code = matches.groupdict()['lang']
                        try:
                            yield GitRepoFile(file_path, self.vcs, lang_code, filename, subdirs)
                        except Language.DoesNotExist:
                            logger.warning("Language does not exist for %s: %s" % (self.vcs, lang_code))

    def pull_translation_files(self):
        for repo_file in self.find_translation_files():
            repo_file.sync()

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
