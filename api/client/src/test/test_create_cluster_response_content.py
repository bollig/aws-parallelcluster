"""
    ParallelCluster

    ParallelCluster API  # noqa: E501

    The version of the OpenAPI document: 3.0.0
    Generated by: https://openapi-generator.tech
"""


import sys
import unittest

import pcluster.client
from pcluster.client.model.cluster_info_summary import ClusterInfoSummary
from pcluster.client.model.config_validation_message import ConfigValidationMessage
globals()['ClusterInfoSummary'] = ClusterInfoSummary
globals()['ConfigValidationMessage'] = ConfigValidationMessage
from pcluster.client.model.create_cluster_response_content import CreateClusterResponseContent


class TestCreateClusterResponseContent(unittest.TestCase):
    """CreateClusterResponseContent unit test stubs"""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testCreateClusterResponseContent(self):
        """Test CreateClusterResponseContent"""
        # FIXME: construct object with mandatory attributes with example values
        # model = CreateClusterResponseContent()  # noqa: E501
        pass


if __name__ == '__main__':
    unittest.main()