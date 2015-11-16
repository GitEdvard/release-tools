import click
from release_tools.workflow import Workflow, Conventions, DEVELOP_BRANCH
from release_tools.github import GithubProvider


def create_workflow(owner, repo, whatif):
    provider = GithubProvider(owner, repo)
    return Workflow(provider, Conventions, whatif)


@click.group()
@click.option('--whatif/--not-whatif', default=False)
@click.pass_context
def cli(ctx, whatif):
    ctx.obj['whatif'] = whatif
    if whatif:
        print "*** Running with whatif ON - no writes ***"


@cli.command('create-cand')
@click.argument('owner')
@click.argument('repo')
@click.pass_context
def create_cand(ctx, owner, repo):
    print "Creating a release candidate from {}".format(DEVELOP_BRANCH)
    workflow = create_workflow(owner, repo, ctx.obj['whatif']) 
    workflow.create_release_candidate()


@cli.command('create-hotfix')
@click.argument('owner')
@click.argument('repo')
@click.pass_context
def create_hotfix(ctx, owner, repo):
    print "Creating a hotfix branch"
    workflow = create_workflow(owner, repo, ctx.obj['whatif']) 
    workflow.create_hotfix()


@cli.command('accept')
@click.argument('owner')
@click.argument('repo')
@click.option('--force/--not-force', default=False)
@click.pass_context
def accept(ctx, owner, repo, force):
    print "Accepting the current release candidate"
    workflow = create_workflow(owner, repo, ctx.obj['whatif']) 
    workflow.accept_release_candidate(force)


@cli.command('download')
@click.argument('owner')
@click.argument('repo')
@click.argument('path')
@click.option('--force/--not-force', default=False)
@click.pass_context
def download(ctx, owner, repo, path, force):
    print "Downloading the next release in the queue"
    workflow = create_workflow(owner, repo, ctx.obj['whatif']) 
    workflow.download_next_in_queue(path, force)


@cli.command()
@click.argument('owner')
@click.argument('repo')
@click.pass_context
def latest(ctx, owner, repo):
    workflow = create_workflow(owner, repo, ctx.obj['whatif']) 
    latest_version = workflow.get_latest_version()
    print "Latest version: {0}".format(latest_version)


@cli.command()
@click.argument('owner')
@click.argument('repo')
@click.pass_context
def status(ctx, owner, repo):
    workflow = create_workflow(owner, repo, ctx.obj['whatif']) 

    branches = workflow.provider.get_branches()
    branch_names = [branch["name"] for branch in branches]

    queue = workflow.get_queue()

    latest_version = workflow.get_latest_version()
    next_version = workflow.get_candidate_version()
    hotfix_version = workflow.get_hotfix_version()
    print "Latest version: {}".format(latest_version)
    print "  - Next version version would be: {}".format(next_version)
    print "  - Next hotfix version would be: {}".format(hotfix_version)

    # TODO: Report all release tags too

    print ""
    print "Branches:"
    for branch in branch_names:
        print "  {}{}".format(branch, " *" if (branch in queue) else "")

    print ""
    print "Queue:"
    # TODO: Use cache for api calls when possible
    for branch in queue:
        pull_requests = len(workflow.provider.get_pull_requests(branch))
        print "  {} (PRs={})".format(branch, pull_requests)

    # TODO: Compare relevant branches
    print ""


def cli_main():
    cli(obj={})

if __name__ == "__main__":
    #import logging
    #logging.basicConfig(level=logging.DEBUG)
    cli_main()

