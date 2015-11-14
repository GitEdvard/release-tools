#!/usr/bin/env python

# Unit tests

import unittest
from release_tools.github import Version

class TestVersioning(unittest.TestCase):
    """
    Tests code that has to do with versioning, mapping
    to/from tags or branches to versions
    """
    def test_can_create_version_from_string(self):
        string = "1.2.3"
        version = Version.from_string(string)
        self.assertEqual(version, (1, 2, 3))

    def test_can_change_version(self):
        version = Version([1, 2, 3])
        new_version = version.inc_patch().inc_major().inc_minor()
        self.assertEqual(new_version, (2, 3, 4))

    def test_get_correct_version_from_tag(self):
        tag = "v1.2.3"
        from release_tools.github import get_version_from_tag
        version = get_version_from_tag(tag)
        self.assertEqual(version, (1, 2, 3))

class TestWorkflow(unittest.TestCase):
    pass

class TestGithub(unittest.TestCase):
    pass

if __name__ == "__main__":
    unittest.main()

