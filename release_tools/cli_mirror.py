"""
CLI tool for mirroring selected branches between two git remotes.

This tool is made available for the scenario where your release process
requires you to synch two remotes, e.g. when using GitLab CI internally
for validation and deployment, but your code (or part of it) is hosted on GitHub.
"""
import click
import yaml


@click.group()
@click.option('--whatif/--not-whatif', default=False)
@click.option('--config')
@click.pass_context
def cli(ctx, whatif, config):
    ctx.obj['whatif'] = whatif
    with open(config) as fs:
        ctx.obj['config'] = yaml.load(fs)

    print ctx


"""
!/bin/bash
# Set this up as a daemon, synchs, then sleeps for 30 seconds.
# (TODO: rewrite in something more manageable, e.g. Python)
set -e

# NOTE: Actually using the withrocks fork instead of Molmed while testing:
while true
do
  echo "Synching repos..."
  synch_private_repo "git@github.com:withrocks/clarity-snpseq.git" clarity-snpseq
  echo "Done synching, sleeping for 10 seconds..."
  sleep 10
done
"""

