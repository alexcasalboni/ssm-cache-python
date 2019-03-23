""" Test filters support """
import os
import boto3
import placebo
from . import TestBase

from ssm_cache import SSMParameter, SSMParameterGroup
from ssm_cache.filters import (
    SSMFilter,
    SSMFilterName,
    SSMFilterType,
    SSMFilterKeyId,
    SSMFilterPath,
)


class TestSSMFilters(TestBase):
    """ Test Filters """

    PLACEBO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'placebo/filters'))

    def setUp(self):
        session = boto3.Session()
        pill = placebo.attach(session, data_path=self.PLACEBO_PATH)
        pill.playback()
        ssm_client = session.client('ssm')
        SSMParameter.set_ssm_client(ssm_client)

    def test_filter_interface(self):
        """ Test filter interface """
        filter_obj = SSMFilter(
            key=SSMFilter.KEY_NAME,
        )
        filter_dict = filter_obj.to_dict()
        self.assertIn('Key', filter_dict)
        self.assertEqual(filter_dict['Key'], SSMFilter.KEY_NAME)
        self.assertIn('Option', filter_dict)
        self.assertEqual(filter_dict['Option'], SSMFilter.OPTION_EQUALS)
        self.assertNotIn('Values', filter_dict)

        filter_obj.value('TestValue')
        filter_dict = filter_obj.to_dict()
        self.assertIn('Values', filter_dict)
        self.assertIsInstance(filter_dict['Values'], list)
        self.assertEqual(len(filter_dict['Values']), 1)
        self.assertEqual(filter_dict['Values'][0], 'TestValue')

    def test_filter_interface_invalid(self):
        """ Test filter interface errors """
        with self.assertRaises(ValueError):
            _ = SSMFilter(key="Invalid name")

    def test_filter_max_values(self):
        """ Test filter interface errors """
        filter_obj = SSMFilter(
            key=SSMFilter.KEY_NAME,
        )

        for index in range(50):
            filter_obj.value(index)

        with self.assertRaises(ValueError):
            filter_obj.value("51th value")

    def test_filter_option_beginswith(self):
        """ Test filter interface """
        filter_obj = SSMFilter(
            key=SSMFilter.KEY_NAME,
            option=SSMFilter.OPTION_BEGINSWITH,
        )
        filter_dict = filter_obj.to_dict()
        self.assertIn('Option', filter_dict)
        self.assertEqual(filter_dict['Option'], SSMFilter.OPTION_BEGINSWITH)

    def test_filter_option_path(self):
        """ Test filter interface """
        filter_obj = SSMFilter(
            key=SSMFilter.KEY_PATH,
            option=SSMFilter.OPTION_RECURSIVE,
        )
        filter_dict = filter_obj.to_dict()
        self.assertIn('Option', filter_dict)
        self.assertEqual(filter_dict['Option'], SSMFilter.OPTION_RECURSIVE)

    def test_filter_option_invalid(self):
        """ Test filter interface """
        with self.assertRaises(ValueError):
            _ = SSMFilter(
                key=SSMFilter.KEY_PATH,
                option=SSMFilter.OPTION_EQUALS,
            )
        with self.assertRaises(ValueError):
            _ = SSMFilter(
                key=SSMFilter.KEY_PATH,
                option=SSMFilter.OPTION_BEGINSWITH,
            )
        with self.assertRaises(ValueError):
            _ = SSMFilter(
                key=SSMFilter.KEY_NAME,
                option=SSMFilter.OPTION_RECURSIVE,
            )
        with self.assertRaises(ValueError):
            _ = SSMFilter(
                key=SSMFilter.KEY_NAME,
                option=SSMFilter.OPTION_ONELEVEL,
            )

    def test_filter_name(self):
        """ Test filter interface """
        with self.assertRaises(NotImplementedError):
            _ = SSMFilterName()

        # filter_dict = filter_obj.to_dict()
        # self.assertIn('Key', filter_dict)
        # self.assertEqual(filter_dict['Key'], SSMFilter.KEY_NAME)
        # self.assertIn('Option', filter_dict)
        # self.assertEqual(filter_dict['Option'], SSMFilter.OPTION_EQUALS)

    def test_filter_type(self):
        """ Test filter interface """
        filter_obj = SSMFilterType()

        filter_dict = filter_obj.to_dict()
        self.assertIn('Key', filter_dict)
        self.assertEqual(filter_dict['Key'], SSMFilter.KEY_TYPE)
        self.assertIn('Option', filter_dict)
        self.assertEqual(filter_dict['Option'], SSMFilter.OPTION_EQUALS)

        with self.assertRaises(ValueError):
            filter_obj.value('InvalidValue')

        filter_obj.value(SSMFilterType.TYPE_SECURESTRING)

        filter_dict = filter_obj.to_dict()
        self.assertEqual(len(filter_dict['Values']), 1)
        self.assertEqual(filter_dict['Values'][0], SSMFilterType.TYPE_SECURESTRING)

    def test_filter_keyid(self):
        """ Test filter interface """
        filter_obj = SSMFilterKeyId()

        filter_dict = filter_obj.to_dict()
        self.assertIn('Key', filter_dict)
        self.assertEqual(filter_dict['Key'], SSMFilter.KEY_KEYID)
        self.assertIn('Option', filter_dict)
        self.assertEqual(filter_dict['Option'], SSMFilter.OPTION_EQUALS)

    def test_filter_path(self):
        """ Test filter interface """
        with self.assertRaises(NotImplementedError):
            _ = SSMFilterPath()

        # filter_dict = filter_obj.to_dict()
        # self.assertIn('Key', filter_dict)
        # self.assertEqual(filter_dict['Key'], SSMFilter.KEY_PATH)
        # self.assertIn('Option', filter_dict)
        # self.assertEqual(filter_dict['Option'], SSMFilter.OPTION_RECURSIVE)

    def test_filter_chainability(self):
        """ Test filter interface """
        filter_obj = SSMFilterKeyId()

        filter_obj\
            .value('Value1')\
            .value('Value2')\
            .value('Value3')

        filter_dict = filter_obj.to_dict()
        self.assertEqual(len(filter_dict['Values']), 3)

        filter_obj\
            .values(['Value4', 'Value5'])\
            .values(['Value6', 'Value7'])\
            .values(['Value8', 'Value9', 'Value10'])

        filter_dict = filter_obj.to_dict()
        self.assertEqual(len(filter_dict['Values']), 10)




    def test_integration(self):
        """ Test filters integration """
        # note: moto doesn't implement filters yet
        # GitHub issue here: https://github.com/spulec/moto/issues/1517

        # the following code was used to generate placebo's files
        # names = [
        #     "/filters-test/my_param_1",
        #     "/filters-test/my_param_2",
        #     "/filters-test/another_param",
        # ]
        # self._create_params(names)
        # list_names = ["/filters-test/my_params_list"]
        # self._create_params(names=list_names, parameter_type="StringList")
        # secure_names = ["/filters-test/my_secure_param"]
        # self._create_params(names=secure_names, parameter_type="SecureString")


        group = SSMParameterGroup()

        # manual filter definition
        params = group.parameters(
            path="/filters-test",
            filters=[{
                'Key': 'Type',
                'Option': 'Equals',
                'Values': ['StringList']
            }],
        )
        self.assertEqual(len(params), 1)

        # class-based filter
        params = group.parameters(
            path="/filters-test",
            filters=[SSMFilterType().value('StringList')],
        )
        self.assertEqual(len(params), 1)

        params = group.parameters(
            path="/filters-test",
            filters=[SSMFilterType().value('SecureString')],
        )
        self.assertEqual(len(params), 1)

        params = group.parameters(
            path="/filters-test",
            filters=[SSMFilterType().value('String')],
        )
        self.assertEqual(len(params), 3)

        params = group.parameters(
            path="/filters-test",
            filters=[SSMFilterKeyId().value('alias/aws/ssm')],
        )
        self.assertEqual(len(params), 1)

        params = group.parameters(
            path="/filters-test",
            filters=[SSMFilterKeyId('BeginsWith').value('alias/')],
        )
        self.assertEqual(len(params), 1)

        # params = group.parameters(
        #     path="/filters-test",
        #     filters=[SSMFilterPath().value('my_param_')],
        # )
        # self.assertEqual(len(params), 1)

        # params = group.parameters(
        #     path="/filters-test",
        #     filters=[SSMFilterName('BeginsWith').value('my_param_')],
        # )
        # self.assertEqual(len(params), 1)
        