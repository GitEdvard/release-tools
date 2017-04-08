import os
import logging


class RepoInfo(object):
    def __init__(self, name, source, target):
        """
        :param name: The name of the repo, e.g.: release-tools
        :param source: The source url, e.g.: git@github.com:withrocks/release-tools.git
        :param target: The target url, e.g.: git@gitlab-local:withrocks/release-tools.git
        :return:
        """
        self.name = name
        self.source = source
        self.target = target
        self.deploy_key = self.get_deployment_key()

    def get_deployment_key(self):
        """
        If we have an SSH key with the same name as this repo, we can assume that this is
        a private repository.
        """
        path = os.path.expanduser("~/.ssh/{}".format(self.name))
        if os.path.exists(path):
            return path
        else:
            return None

    @property
    def is_private(self):
        return self.deploy_key is not None

    def __repr__(self):
        return repr(self.__dict__)


def clone(repo_info):
    """Clones using the source remote. Uses deploy keys if necessary"""
    pass
