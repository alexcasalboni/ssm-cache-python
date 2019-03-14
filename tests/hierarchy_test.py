""" Test ssm_cache/cache.py hierarchical params """
from __future__ import print_function
import os
import sys
from datetime import datetime, timedelta
from freezegun import freeze_time
from . import TestBase

from ssm_cache import SSMParameterGroup, SSMParameter, InvalidPathError


# pylint: disable=protected-access
class TestSSMHierarchy(TestBase):
    """ Hierarchical parameters tests """

    HIERARCHY_ROOT = "/Root"
    HIERARCHY_PREPATH_SIMPLE = "/Level1/Level2"
    HIERARCHY_PREPATH = "%s%s" % (HIERARCHY_ROOT, HIERARCHY_PREPATH_SIMPLE)
    HIERARCHY_PREPATH_LIST_SIMPLE = "/LevelA/LevelB"
    HIERARCHY_PREPATH_LIST = "%s%s" % (HIERARCHY_ROOT, HIERARCHY_PREPATH_LIST_SIMPLE)
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
        group = SSMParameterGroup()
        params = group.parameters(self.HIERARCHY_PREPATH)
        self.assertEqual(len(group), self.GROUP_SIZE)
        for parameter in params:
            self.assertEqual(parameter.value, self.PARAM_VALUE)
            self.assertTrue(self.HIERARCHY_PREPATH in parameter.name)

    def test_hierarchy_cache(self):
        """ Test group hierarchy caching """
        group = SSMParameterGroup()  # without max age
        group.parameters(self.HIERARCHY_PREPATH)
        self.assertFalse(
            group._should_refresh(),
            "Cache-less groups shouldn't ever refresh",
        )

        group = SSMParameterGroup(max_age=10)   # wit max age
        group.parameters(self.HIERARCHY_PREPATH)
        self.assertFalse(
            group._should_refresh(),
            "Cache-full groups shouldn't need refresh immediately after initialization",
        )

        group = SSMParameterGroup(max_age=10)   # wit max age
        group.parameters(self.HIERARCHY_PREPATH)
        # freeze_time will pretend 10 seconds have passed!
        with freeze_time(lambda: datetime.utcnow() + timedelta(seconds=10)):
            self.assertTrue(
                group._should_refresh(),
                "Cache-full groups should need refresh after time has passed",
            )

        group = SSMParameterGroup(max_age=10)   # wit max age
        group.parameters(self.HIERARCHY_PREPATH)
        self.assertFalse(group._should_refresh())
        # freeze_time will pretend 10 seconds have passed!
        with freeze_time(lambda: datetime.utcnow() + timedelta(seconds=10)):
            group.parameters(self.HIERARCHY_PREPATH_LIST)
            self.assertTrue(
                group._should_refresh(),
                "Cache-full groups should need refresh based on the oldest fetched params",
            )


    def test_hierarchy_with_lists(self):
        """ Test group hierarchy with lists """
        group = SSMParameterGroup()
        params = group.parameters(self.HIERARCHY_PREPATH_LIST)
        self.assertEqual(len(group), self.GROUP_SIZE)
        for parameter in params:
            self.assertIsInstance(parameter.value, list)
            for value in parameter.value:
                self.assertEqual(value, self.PARAM_VALUE)
            self.assertTrue(self.HIERARCHY_PREPATH_LIST in parameter.name)

    def test_hierarchy_root(self):
        """ Test group hierarchy root """
        group = SSMParameterGroup()
        params = group.parameters(self.HIERARCHY_ROOT)
        self.assertEqual(len(params), self.GROUP_SIZE * 2)
        self.assertEqual(len(group), self.GROUP_SIZE * 2)
        for parameter in params:
            self.assertTrue(self.HIERARCHY_ROOT in parameter.name)

    def test_hierarchy_multiple(self):
        """ Test group hierarchy multiple calls """
        group = SSMParameterGroup()
        params_1 = group.parameters(self.HIERARCHY_PREPATH)
        params_2 = group.parameters(self.HIERARCHY_PREPATH_LIST)
        self.assertEqual(len(params_1), self.GROUP_SIZE)
        self.assertEqual(len(params_2), self.GROUP_SIZE)
        self.assertEqual(len(group), self.GROUP_SIZE * 2)
        for parameter in params_1:
            self.assertTrue(self.HIERARCHY_PREPATH in parameter.name)
            self.assertTrue(self.HIERARCHY_ROOT in parameter.name)
            self.assertTrue(parameter.name.startswith(self.HIERARCHY_PREPATH))

        for parameter in params_2:
            self.assertTrue(self.HIERARCHY_PREPATH_LIST in parameter.name)
            self.assertTrue(self.HIERARCHY_ROOT in parameter.name)
            self.assertTrue(parameter.name.startswith(self.HIERARCHY_PREPATH_LIST))

    def test_hierarchy_multiple_overlap(self):
        """ Test group hierarchy multiple overlapping calls """
        group = SSMParameterGroup()
        params_1 = group.parameters(self.HIERARCHY_PREPATH)
        params_all = group.parameters(self.HIERARCHY_ROOT)
        self.assertEqual(len(params_1), self.GROUP_SIZE)
        self.assertEqual(len(params_all), self.GROUP_SIZE * 2)
        self.assertEqual(len(group), self.GROUP_SIZE * 2)
        for parameter in params_1:
            self.assertTrue(self.HIERARCHY_PREPATH in parameter.name)
            self.assertTrue(self.HIERARCHY_ROOT in parameter.name)
        for parameter in params_all:
            self.assertTrue(self.HIERARCHY_ROOT in parameter.name)

    def test_hierarchy_prefix(self):
        """ Test group hierarchy prefix with multiple parameters """
        group = SSMParameterGroup(base_path=self.HIERARCHY_ROOT)
        params_1 = group.parameters(self.HIERARCHY_PREPATH_SIMPLE)
        params_2 = group.parameters(self.HIERARCHY_PREPATH_LIST_SIMPLE)
        self.assertEqual(len(params_1), self.GROUP_SIZE)
        self.assertEqual(len(params_2), self.GROUP_SIZE)
        self.assertEqual(len(group), self.GROUP_SIZE * 2)
        for parameter in params_1:
            self.assertTrue(self.HIERARCHY_PREPATH in parameter.name)
            self.assertTrue(self.HIERARCHY_ROOT in parameter.name)
            self.assertTrue(parameter.name.startswith(self.HIERARCHY_PREPATH))

        for parameter in params_2:
            self.assertTrue(self.HIERARCHY_PREPATH_LIST in parameter.name)
            self.assertTrue(self.HIERARCHY_ROOT in parameter.name)
            self.assertTrue(parameter.name.startswith(self.HIERARCHY_PREPATH_LIST))

    def test_hierarchy_prefix_single(self):
        """ Test group hierarchy prefix with single parameter """
        group = SSMParameterGroup(base_path=self.HIERARCHY_ROOT)
        param = group.parameter("%s/my_param_1" % self.HIERARCHY_PREPATH_SIMPLE)
        self.assertEqual(len(group), 1)
        self.assertTrue(self.HIERARCHY_PREPATH in param.name)
        self.assertTrue(self.HIERARCHY_ROOT in param.name)
        self.assertEqual(param.value, self.PARAM_VALUE)

    def test_hierarchy_prefix_mixed(self):
        """ Test group hierarchy prefix with mixed parameters """
        group = SSMParameterGroup(base_path=self.HIERARCHY_ROOT)
        param = group.parameter("%s/my_param_1" % self.HIERARCHY_PREPATH_SIMPLE)
        params_1 = group.parameters(self.HIERARCHY_PREPATH_SIMPLE)
        params_2 = group.parameters(self.HIERARCHY_PREPATH_LIST_SIMPLE)
        self.assertIsInstance(param, SSMParameter)
        self.assertEqual(len(params_1), self.GROUP_SIZE)
        self.assertEqual(len(params_2), self.GROUP_SIZE)
        self.assertEqual(len(group), self.GROUP_SIZE * 2)

    def test_hierarchy_prefix_complex(self):
        """ Test group hierarchy prefix (complex) """
        names = [
            "/PrefixComplex/Foo/Bar",
            "/PrefixComplex/Foo/Baz/1",
            "/PrefixComplex/Foo/Baz/2",
            "/PrefixComplex/Foo/Taz/1",
            "/PrefixComplex/Foo/Taz/2",
        ]
        self._create_params(names)
        group = SSMParameterGroup(base_path="/PrefixComplex/Foo")
        bar_param = group.parameter("/Bar")
        baz_params = group.parameters("/Baz")
        taz_params = group.parameters("/Taz")
        self.assertIsInstance(bar_param, SSMParameter)
        self.assertEqual(len(baz_params), 2)
        self.assertEqual(len(taz_params), 2)
        self.assertEqual(len(group), 5)

    def test_hierarchy_recursive(self):
        """ Test group hierarchy prefix (recursive) """
        names = [
            "/PrefixRecursive/Foo/Baz/1",
            "/PrefixRecursive/Foo/Baz/2",
            "/PrefixRecursive/Foo/Baz/Taz/1",
            "/PrefixRecursive/Foo/Baz/Taz/2",
        ]
        self._create_params(names)
        group = SSMParameterGroup(base_path="/PrefixRecursive/Foo")
        baz_params = group.parameters("/Baz")
        self.assertEqual(len(baz_params), 4)
        self.assertEqual(len(group), 4)

    def test_hierarchy_not_recursive(self):
        """ Test group hierarchy prefix (not recursive) """
        names = [
            "/PrefixNotRecursive/Foo/Baz/1",
            "/PrefixNotRecursive/Foo/Baz/2",
            "/PrefixNotRecursive/Foo/Baz/Taz/1",
            "/PrefixNotRecursive/Foo/Baz/Taz/2",
        ]
        self._create_params(names)
        group = SSMParameterGroup(base_path="/PrefixNotRecursive/Foo")
        baz_params = group.parameters("/Baz", recursive=False)
        taz_params = group.parameters("/Baz/Taz")
        self.assertEqual(len(baz_params), 2)
        self.assertEqual(len(taz_params), 2)
        self.assertEqual(len(group), 4)

    def test_hierarchy_prefix_errors(self):
        """ Test group hierarchy prefix errors """
        with self.assertRaises(InvalidPathError):
            _ = SSMParameterGroup(base_path="InvalidPrefix")

        group = SSMParameterGroup(base_path=self.HIERARCHY_ROOT)

        # note: this raises only because the group has a base path
        with self.assertRaises(InvalidPathError):
            _ = group.parameter("InvalidPath")

        with self.assertRaises(InvalidPathError):
            _ = group.parameters("InvalidPath")

