import unittest
import os
import sys

import boto3
import placebo

from mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ssm_cache import SSMParameter

class TestClientOverride(unittest.TestCase):
    def testWithPlacebo(self):
        session = boto3.Session()
        pill = placebo.attach(session, data_path=os.path.abspath(os.path.join(os.path.dirname(__file__), 'placebo')))
        pill.playback()

        client = session.client('ssm')

        SSMParameter.set_ssm_client(client)

        cache = SSMParameter("my_param")
        self.assertEqual(cache.value, "expected value")

        # reset to a proper client
        SSMParameter.set_ssm_client(boto3.Session().client('ssm'))

    def testWithIllegalClient(self):
        with self.assertRaises(TypeError):
            SSMParameter.set_ssm_client(42)
