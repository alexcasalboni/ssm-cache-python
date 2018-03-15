""" Test ssm_cache/cache.py main functionalities """
from __future__ import print_function
import os
import sys
from moto import mock_ssm
from . import TestBase

# pylint: disable=wrong-import-order,wrong-import-position

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ssm_cache import SSMParameterGroup


# pylint: disable=protected-access
@mock_ssm
class TestSSMHierarchy(TestBase):
    """ Hierarchical parameters tests """

    HIERARCHY_ROOT = "/Root"
    HIERARCHY_PREPATH = "%s/Level1/Level2" % HIERARCHY_ROOT
    HIERARCHY_PREPATH_LIST = "%s/LevelA/LevelB" % HIERARCHY_ROOT
    GROUP_SIZE = 20

    def setUp(self):
        names = [
            "%s/my_param_%d" % (self.HIERARCHY_PREPATH, i)
            for i in range(self.GROUP_SIZE)
        ]
        self._create_params(names)
        list_names = [
            "%s/my_param_list_%d" % (self.HIERARCHY_PREPATH_LIST, i)
            for i in range(self.GROUP_SIZE)
        ]
        self._create_params(names=list_names, parameter_type="StringList")

    def test_hierarchy(self):
        """ Test group hierarchy """
        group = SSMParameterGroup(hierarchy_path=self.HIERARCHY_PREPATH)
        self.assertEqual(len(group), self.GROUP_SIZE)
        for parameter in group.parameters:
            self.assertEqual(parameter.value, self.PARAM_VALUE)
            self.assertTrue(self.HIERARCHY_PREPATH in parameter.name)

    def test_hierarchy_with_lists(self):
        """ Test group hierarchy with lists """
        group = SSMParameterGroup(hierarchy_path=self.HIERARCHY_PREPATH_LIST)
        self.assertEqual(len(group), self.GROUP_SIZE)
        for parameter in group.parameters:
            self.assertIsInstance(parameter.value, list)
            for value in parameter.value:
                self.assertEqual(value, self.PARAM_VALUE)
            self.assertTrue(self.HIERARCHY_PREPATH_LIST in parameter.name)

    def test_hierarchy_root(self):
        """ Test group hierarchy root """
        group = SSMParameterGroup(hierarchy_path=self.HIERARCHY_ROOT)
        self.assertEqual(len(group), self.GROUP_SIZE * 2)
        for parameter in group.parameters:
            self.assertTrue(self.HIERARCHY_ROOT in parameter.name)
