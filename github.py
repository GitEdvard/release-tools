#!/usr/bin/env python
import requests
import logging
import click
import re
import zipfile
import StringIO
import os
import sys

# Assumes the following branch structure:
#   - develop:        used for the latest version of the code
#   - release-#.#.#:  0-n release branches for candidates
#   - hotfix-#.#.#:   0-n hotfix branches
#   - master:         always contains the latest release, tagged with versions
# Of these branches, there can be 0-1 active hotfix branch and 0-1 active release branch at a time

MASTER_BRANCH = "master"
DEVELOP_BRANCH = "develop"
RELEASE_BRANCH_PRE = "release"
HOTFIX_BRANCH_PRE = "hotfix"

def get_access_token():
    with open('token.secret') as f:
        access_token = f.readline().strip()
        return access_token

def access_token_postfix():
    return "?access_token={}".format(get_access_token())

access_token = get_access_token()

class GithubException(Exception):
    pass

class MergeException(Exception):
    pass

class WorkflowException(Exception):
    pass

class Version(tuple):
    def __repr__(self):
        return ".".join([str(num) for num in self])

    def _make_delta(self, *delta):
        return Version([self[0] + delta[0], self[1] + delta[1], self[2] + delta[2]])

    def inc_major(self):
        return self._make_delta(1, 0, 0)

    def inc_minor(self):
        return self._make_delta(0, 1, 0)

    def inc_patch(self):
        return self._make_delta(0, 0, 1)

    @staticmethod
    def from_string(s):
        return Version(map(int, s.split(".")))

def get_version_from_tag(tag):
    pattern = r"v(?P<major>\d+).(?P<minor>\d+).(?P<patch>\d+)"
    m = re.match(pattern, tag)
    return Version(map(int, (m.group('major'), m.group('minor'), m.group('patch'))))

def get_latest_version(owner, repo):
    url = "https://api.github.com/repos/{}/{}/releases/latest{}".format(owner, repo, access_token_postfix())
    response = requests.get(url)
    if response.status_code == 200:
        json = response.json()
        tag_name = json["tag_name"]
        return get_version_from_tag(tag_name)
    else:
        raise GithubException(response.text)

def get_candidate_version(owner, repo):
    latest = get_latest_version(owner, repo)
    return latest.inc_minor()

def get_hotfix_version(owner, repo):
    latest = get_latest_version(owner, repo)
    return latest.inc_patch()

def get_refs_heads(owner, repo):
    access_token = get_access_token()
    url = "https://api.github.com/repos/{}/{}/git/refs/heads?access_token={}".format(owner, repo, access_token)
    response = requests.get(url)
    return response.json()

def get_refs_head(owner, repo, ref):
    heads = get_refs_heads(owner, repo)
    filtered = [x for x in heads if x["ref"] == ref]
    assert len(filtered) == 1
    return filtered[0]["object"]["sha"]

def create_branch_from_master(owner, repo, new_branch):
    """
    Creates a new branch from the master branch

    If the branch already exists, it will be ignored without an exception
    """
    sha = get_refs_head(owner, repo, "refs/heads/master")

    body = {"ref": "refs/heads/{}".format(new_branch), "sha": sha}
    url = "https://api.github.com/repos/{}/{}/git/refs{}".format(owner, repo, access_token_postfix())
    response = requests.post(url, json=body)

    if response.status_code == 201:
        print "Branch successfully created"
    elif response.status_code == 422:
        print "Branch already exists"  # TODO: Check error code def in docs

def get_candidate_branch(owner, repo):
    version = get_candidate_version(owner, repo)
    return get_branch_name_from_version(version, RELEASE_BRANCH_PRE)

def get_branch_name_from_version(version, prefix):
    """Given a version tuple, returns a valid branch name"""
    return "{}-{}".format(prefix, version)

def get_hotfix_branch(owner, repo):
    version = get_hotfix_version(owner, repo)
    return get_branch_name_from_version(version, HOTFIX_BRANCH_PRE)

def get_tag_from_branch(branch_name):
    """
    Returns the tag we use for tagging the release. Base it on the
    branch name to avoid errors
    """
    # This is kinda ugly
    tag_name = branch_name.replace(RELEASE_BRANCH_PRE + "-", "v")
    tag_name = tag_name.replace(HOTFIX_BRANCH_PRE + "-", "v")
    return tag_name

def merge(owner, repo, base, head, commit_message):
    url = "https://api.github.com/repos/{}/{}/merges{}".format(owner, repo, access_token_postfix())
    json = {"base": base, "head": head, "commit_message": commit_message}
    response = requests.post(url, json=json)
    if response.status_code == 201:
        print "Successfully merged '{}' into '{}'".format(head, base)
    elif response.status_code == 204:
        print "Nothing to merge"
    elif response.status_code == 409:
        raise MergeException(response.text)
    else:
        msg = "Unexpected result code from Github ({}): {}".format(response.status_code, response.text)
        raise GithubException(msg)

def list_pull_requests(owner, repo):
    url = "https://api.github.com/repos/{}/{}/pulls{}".format(owner, repo, access_token_postfix())
    resp = requests.get(url)
    print resp.json()

def create_pull_request(owner, repo, base, head, title, body):
    url = "https://api.github.com/repos/{}/{}/pulls{}".format(owner, repo, access_token_postfix())
    json = {"head": head, "base": base, "title": title, "body": body}
    resp = requests.post(url, json=json)
    if resp.status_code == 201:
        print "A pull request has been created from '{}' to '{}'".format(head, base)
    else:
        print resp.status_code, resp.text

def download_archive(owner, repo, branch, save_to_path, ball="zipball"):
    """Ball can be either zipball or tarball"""
    # TODO: Test on Windows
    url = "https://api.github.com/repos/{owner}/{repo}/{archive_format}/{ref}{token}"\
              .format(owner=owner, repo=repo, archive_format=ball, ref=branch, token=access_token_postfix())
    response = requests.get(url)
    if response.status_code == 200:
        print "Downloaded the archive. Extracting..."
        archive = zipfile.ZipFile(StringIO.StringIO(response.content))
        archive.extractall(save_to_path)
        print "Extracted"

def create_release_candidate(owner, repo, whatif):
    """
    Pre: The master branch has a tagged latest version (TODO: Support if it hasn't)

    The candidate release is based on info from Github about the latest release. For
    this, there should be a new branch, called release-#.#.#. If such a branch already
    exists, no new branch is created.

    The next step is to create a pull request from develop to the new release branch.
    This branch should then be code reviewed and eventually merged.
    """
    candidate_branch = get_candidate_branch(owner, repo)

    print "Creating a new branch, '{}' from master".format(candidate_branch)
    if not whatif:
        create_branch_from_master(owner, repo, candidate_branch)

    # Merge from 'develop' into the new release branch:
    print "Merging from {} to {}".format(DEVELOP_BRANCH, candidate_branch)
    if not whatif:
        merge(owner, repo, candidate_branch, DEVELOP_BRANCH, "Merging '{}' into '{}'".format(DEVELOP_BRANCH, candidate_branch))

def create_hotfix(owner, repo, whatif):
    """
    Creates a hotfix branched off the master.

    Hotfix branches are treated similar to release branches, except the patch number
    has been increased instead and they are before the release in the deployment pipeline.
    """
    hotfix_branch = get_hotfix_branch(owner, repo)
    print "Creating a new hotfix branch, '{}' from master".format(hotfix_branch)
    if not whatif:
        create_branch_from_master(owner, repo, hotfix_branch)

    print "Not merging automatically into a hotfix - hotfix patches should be sent as pull requests to it"

def download_next_in_queue(owner, repo, path, force, whatif):
    queue = get_queue(owner, repo)
    if len(queue) > 1:
        print "There are more than one items in the queue. Downloading the first item."

    branch = queue[0]

    full_path = os.path.join(path, branch)
    if not force and os.path.exists(full_path):
        print "There already exists a directory for the build at '{}'. Please specify a non-existing path or --force.".format(full_path)
        sys.exit(1)
    print "Downloading and extracting '{}' to '{}'. This may take a few seconds...".format(branch, full_path)
    if not whatif:
        download_archive(owner, repo, branch, full_path)

def get_hotfix_branches(branch_names):
    """Returns the version numbers for all hotfix branches defined"""
    for branch_name in branch_names:
        if branch_name.startswith(HOTFIX_BRANCH_PRE):
            yield branch_name

def get_release_branches(branch_names):
    """Returns the version numbers for all hotfix branches defined"""
    for branch_name in branch_names:
        if branch_name.startswith(RELEASE_BRANCH_PRE):
            yield branch_name

def get_pending_hotfix_branches(current_version, branch_names):
    for branch in get_hotfix_branches(branch_names):
        branch_version = Version.from_string(branch.split("-")[1])
        if branch_version[0] == current_version[0] and \
           branch_version[1] == current_version[1] and \
           branch_version[2] > current_version[2]:
            yield branch

def get_pending_release_branches(current_tag, branch_names):
    for branch in get_release_branches(branch_names):
        branch_version = Version.from_string(branch.split("-")[1])
        if branch_version[0] > current_tag[0] or \
           branch_version[1] > current_tag[1]:
            yield branch

def get_queue(owner, repo):
    """
    Returns the queue. The queue can only exist of 0..1 release branches
    and 0..1 hotfix branches.

    The hotfix branch will always come before the release branch
    """
    branches = get_branches(owner, repo)
    branch_names = [branch["name"] for branch in branches]
    current_version = get_latest_version(owner, repo)

    pending_hotfixes = list(get_pending_hotfix_branches(current_version, branch_names))
    pending_releases = list(get_pending_release_branches(current_version, branch_names))

    if len(pending_hotfixes) > 1:
        raise WorkflowException("Unexpected number of pending hotfixes: {}".format(len(pending_hotfixes)))

    if len(pending_releases) > 1:
        raise WorkflowException("Unexpected number of pending releases: {}".format(len(pending_releases)))

    queue = pending_hotfixes + pending_releases
    return queue

def accept_release_candidate(owner, repo, force, whatif):
    """
    Accept the next item in the queue

    Merge from release-x.x.x into master and tag master with vx.x.x

    If force is not set to True, the user will be prompted if more than one
    release is in the queue.
    """
    queue = get_queue(owner, repo)

    if len(queue) == 0:
        print "The queue is empty. Nothing to accept."
        return

    branch = queue[0]
    next_release = None

    if len(queue) > 1:
        print "There are more than one item in the queue:"
        for current in queue:
            print "  {}".format(current)

        if not force:
            print "The first branch '{}' will be accepted. Continue?".format(branch)
            accepted = raw_input("y/n> ")

            if accepted != "y":
                print "Action cancelled by user"
                return
        else:
            print "Force set to true. The first branch will automatically be accepted"

        next_release = queue[1]

    def merge_cond(whatif, owner, repo, base, head):
        msg = "Merging from '{}' to '{}'".format(head, base)
        print msg
        if not whatif:
            try:
                merge(owner, repo, base, head, msg)
            except MergeException:
                print "Merge exception while merging '{}' to '{}'. " + \
                      "This can happen if there was a hotfix release in between."\
                      .format(head, base)
                sys.exit(1)

    merge_cond(whatif, owner, repo, MASTER_BRANCH, branch)

    tag_name = get_tag_from_branch(branch)
    print "Tagging HEAD on {} as release {}".format(MASTER_BRANCH, tag_name)
    if not whatif:
        tag_release(owner, repo, tag_name, MASTER_BRANCH)

    if branch.startswith("hotfix"):
        # We don't know if the dev needs this in 'develop' and in the next release, but it's likely
        # so we send a pull request to those.
        # TODO: Don't accept if there is a pull request on a release branch
        # TODO: Branch
        # TODO: Does it work to create pull requests into both?
        print "Hotfix branch merged - sending pull requests to develop and release"
        print "These pull requests need to be reviewed and potential merge conflicts resolved"

        msg = "Apply hotfix '{}' to '{}'".format(branch, DEVELOP_BRANCH)
        body = "Pull request was made automatically by release-tools"
        create_pull_request(owner, repo, DEVELOP_BRANCH, branch, msg, body)

        if next_release:
            msg = "Apply hotfix '{}' to '{}'".format(branch, next_release)
            body = "Pull request was made automatically by release-tools"
            create_pull_request(owner, repo, next_release, branch, msg, body)

def compare(owner, repo, base, head):
    url = "https://api.github.com/repos/{}/{}/compare/{}...{}{}"\
          .format(owner, repo, base, head, access_token_postfix())
    response = requests.get(url)
    print response.status_code, response.json()

def get_branches(owner, repo):
    url = "https://api.github.com/repos/{}/{}/branches{}".format(owner, repo, access_token_postfix())
    response = requests.get(url)
    return response.json()

def tag_release(owner, repo, tag_name, branch):
    # Tags a commit as a release on Github
    url = "https://api.github.com/repos/{}/{}/releases{}".format(owner, repo, access_token_postfix())
    # TODO: Release description
    json = {"tag_name": tag_name, "target_commitish": branch,
            "name": tag_name, "body": "", "draft": False, "prerelease": False}
    response = requests.post(url, json=json)
    if response.status_code == 201:
        print "HEAD of master marked as release {}".format(tag_name)
    else:
        raise GithubException(respones.text)

@click.group()
@click.option('--whatif/--not-whatif', default=False)
@click.pass_context
def cli(ctx, whatif):
    ctx.obj['whatif'] = whatif
    if whatif:
        print "*** Running with whatif ON - no writes ***"
    pass

@cli.command('create-cand')
@click.argument('owner')
@click.argument('repo')
@click.pass_context
def create(ctx, owner, repo):
    print "Creating a release candidate from {}".format(DEVELOP_BRANCH)
    create_release_candidate(owner, repo, ctx.obj['whatif'])

@cli.command('create-hotfix')
@click.argument('owner')
@click.argument('repo')
@click.pass_context
def create(ctx, owner, repo):
    print "Creating a hotfix branch"
    create_hotfix(owner, repo, ctx.obj['whatif'])

@cli.command('accept')
@click.argument('owner')
@click.argument('repo')
@click.option('--force/--not-force', default=False)
@click.pass_context
def accept(ctx, owner, repo, force):
    print "Accepting the current release candidate"
    accept_release_candidate(owner, repo, force, ctx.obj['whatif'])

@cli.command('download')
@click.argument('owner')
@click.argument('repo')
@click.argument('path')
@click.option('--force/--not-force', default=False)
@click.pass_context
def download(ctx, owner, repo, path, force):
    print "Downloading the next release in the queue"
    download_next_in_queue(owner, repo, path, force, ctx.obj['whatif'])

@cli.command()
@click.argument('owner')
@click.argument('repo')
@click.pass_context
def latest(ctx, owner, repo):
    latest = get_latest_version(owner, repo)
    print "Latest version: {0}".format(latest)

@cli.command()
@click.argument('owner')
@click.argument('repo')
@click.pass_context
def status(ctx, owner, repo):
    branches = get_branches(owner, repo)
    branch_names = [branch["name"] for branch in branches]

    queue = get_queue(owner, repo)

    latest = get_latest_version(owner, repo)
    print "Latest version: {}".format(latest)

    # TODO: Report all release tags too

    candidate_branch = get_candidate_branch(owner, repo)
    hotfix_branch = get_hotfix_branch(owner, repo)

    print ""
    print "Branches:"
    for branch in branch_names:
        print "  {}{}".format(branch, " *" if (branch in queue) else "")

    print ""
    print "Queue:"
    # TODO: Use cache for api calls when possible
    for branch in queue:
        print "  {}".format(branch)

    # TODO: Compare relevant branches
    print ""

if __name__ == "__main__":
    cli(obj={})

