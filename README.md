release-tools
-------------

Python tools for handling versioned releases. Currently only handles releases using a particular workflow
(see below) and hosting on Github.

**Install**

pip install -U git://github.com/withrocks/release-tools.git#egg=release-tools

or, with a version:

pip install -U git://github.com/withrocks/release-tools.git@v0.1.2#egg=release-tools


*The tool may work in an unexpected manner if the master branch is changed without the use
of this tool or if release/hotfix branches are made manually.*

**Assumptions**

The release workflow supported assumes that you've got two permanent branches:
  * ``develop``: The next version to be released. Nothing should be committed in here that cannot safely go
  out with the next scheduled release
  * ``master``: Contains the latest version of the released software and tags for all previous releases

The following transient branches also exist:
  * ``release-#.#.#``: Release branches. Can be deleted after releasing.
  * ``hotfix-#.#.#``: Hotfix branches. Can be deleted after releasing.
  * ``feature-branch-n``: Any number of feature branches. Names can be anything not colliding with 
  the other branches

**Workflows**

General flow:
  * Code has been submitted to the ``develop`` branch, probably through pull requests from feature branches
  * When the next version is ready to be released, run ``github.py create-cand <owner> <repo>``
  * This creates a new release branch called ``release-#.#.#``, where the minor version has been increased.
  * Build and validate (separate workflow). Latest version can be fetched through
  ``github.py download <owner> <repo>``. Deploy if validated.
  * After deploying, call ``github.py accept <owner> <repo>``. If the queue also contains a hotfix, you
  will be asked which version to release first.
  * The code has now been merged into master with the applicable tag, e.g. v1.1.0.
  
Hotfix flow:
  * The ``develop`` branch is not available (contains features that can't be deployed),
  and you need to create a hotfix.
  * Run ``github.py create-hotfix <owner> <repo>``
  * Get your hotfixes into this branch as it were the ``develop`` branch, probably through
  pull requests from feature branches.
  * When ready, run ``github.py accept <owner> <repo>``. This will accept the hotfix if one exists.
  * A pull request is made from the hotfix branch to ``develop`` and the active release
  branch ``release-#.#.#``. It's not automatically merged since there may be merge conflicts
  or the fix might only make sense in the latest release.
  This acts a reminder of that the fix might need to go into these branches, but it may
  make more sense to only merge the hotfix->release pull request and then make a separate
  pull request from release->develop, since then fewer merge conflicts might need to be solved.
  
Release queue:
  * Using these workflows, there can only be one hotfix version and one release version
  out at the same time.
  * The hotfix will always be next in the queue. Hotfixes are always marked by an increased patch number. 
  That may not always be in accordance with semantic versioning, but currently that's
  the only scheme supported.


