#!/usr/bin/env python
import unittest
from release_tools.github import GithubProvider

# Tests for the github provider, need access to github
# TODO: add caching to the requests for the test
class TestGithubProvider(unittest.TestCase):
    def test_can_get_tag_name(self):
        provider = GithubProvider("withrocks", "release-tools")
        tag_name = provider.get_latest_version_tag_name() 
        self.assertTrue(tag_name.startswith("v"))


if __name__ == "__main__":
    unittest.main()

