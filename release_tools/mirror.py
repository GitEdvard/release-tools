"""Functions for mirroring git remotes"""
import os
import logging
import time
from release_tools import git


def synch_repo(repo_info, source_root):
    """
    Synchronizes selected branches in a repository between two remotes

    :param repo_info:
    :param source_root: The directory containing the code being synched. Not cleared between synchs.
    :return:
    """
    if not os.path.exists(source_root):
        logging.debug("Creating source root '{}'".format(source_root))
        os.makedirs(source_root)
    logging.debug("cd to {}".format(source_root))
    os.chdir(source_root)

    if not os.path.isdir(repo_info.name):
        logging.debug("The directory '{}' does not exist, cloning for the first time".format(repo_info.name))
        git.clone(repo_info)


def start_synch_task(mirror_settings, loop):
    sleep_interval = mirror_settings.get("sleep", 60)
    source = mirror_settings["source"]
    target = mirror_settings["target"]
    name = mirror_settings["name"]
    repo_info = git.RepoInfo(name, source, target)
    logging.debug("Repo info: {}".format(repo_info))
    source_root = os.path.abspath(mirror_settings["path"])
    while True:
        synch_repo(repo_info, source_root)
        logging.debug("Sleeping for {} seconds".format(sleep_interval))
        if not loop:
            break
        time.sleep(sleep_interval)

"""
  if [ ! -d $name ]; then
    echo "Cloning repo for the first time"
    ssh-agent bash -c "ssh-add ~/.ssh/$name > /dev/null && git clone $giturl"
    cd ~/source/$name
    git remote rename origin github
    git remote add gitlab git@localhost:Molmed/clarity-snpseq.git
  else
    echo "Repo already exists"
  fi

  cd ~/source/$name
  ssh-agent bash -c "ssh-add ~/.ssh/$name > /dev/null 2>&1 && git fetch --all"

  # TODO: There may not be a develop branch, but we always have a master branch:
  for branch in develop master staging
  do
    echo "Pulling $branch from github"
    git checkout -B $branch github/$branch
    ssh-agent bash -c "ssh-add ~/.ssh/$name > /dev/null 2>&1 && git pull"

    # TODO: It would be a nice feature to archive branches that were force pushed over, as an extra security feature
    # we actually only expect staging to be force pushed (this feature would be really nice for develop, as force pushing
    # it indicates a serious bug)
    echo "Pushing $branch to gitlab"
   if [ "$branch" == "staging" ]; then
      ssh-agent bash -c "ssh-add ~/.ssh/$name > /dev/null 2>&1 && git push -f gitlab $branch"
    else
      ssh-agent bash -c "ssh-add ~/.ssh/$name > /dev/null 2>&1 && git push gitlab $branch"
    fi
  done
}
"""
