import unittest
from notifier import Notifier
from unittest import mock
import socket



class NotifierTestCase(unittest.TestCase):
    @mock.patch('boto3.Session.client')
    def setUp(self, mock_boto_client):

        self.notifier = Notifier(region='eu-west-2',
                                account='123456789',
                                sns_topic_arn='dummy-arn',
                                es_host='elastic-local.com',
                                es_user='test',
                                es_password='testpass',
                                tag_selector_key='tag',
                                tag_selector_value='value',
                                period_minutes='1',
                                query_string='syslog_identifier: sshd',
                                index_pattern='*')

        self.notifier.previous_timestamp = '1066-10-14T10:11:12.999999Z'


class TestNotifierCheckESIssue(NotifierTestCase):

        @mock.patch('elasticsearch.Elasticsearch.search')
        @mock.patch('notifier.Notifier.get_logs')
        @mock.patch('notifier.Notifier.trigger_sns')
        @mock.patch('notifier.Notifier.put_current_timestamp')
        def test_connection_error(self,
                                  mock_put_current_timestamp,
                                mock_trigger_sns,
                                mock_get_logs,
                                mock_es_client):

            error_header = self.notifier.header + f"encountered an exception:\n\n"

            mock_get_logs.side_effect = socket.timeout('exception')

            message = f"Connection error for host {self.notifier.es_host} - exception"

            self.notifier.check_es_issue()

            mock_trigger_sns.assert_called_with([error_header + message])

            mock_put_current_timestamp.assert_not_called()

        @mock.patch('elasticsearch.Elasticsearch.search')
        @mock.patch('notifier.Notifier.get_logs')
        @mock.patch('notifier.Notifier.put_current_timestamp')
        def test_events_returned(self,
                                mock_put_current_timestamp,
                                mock_get_logs,
                                mock_es_client):

            mock_get_logs.return_value = [{'a': 'b'}]

            events = self.notifier.check_es_issue()

            self.assertTrue(events == [{'a': 'b'}])

            mock_put_current_timestamp.assert_called_with(self.notifier.ssm_client, self.notifier.current_timestamp)

        @mock.patch('boto3.Session.client')
        def test_get_instance_from_private_dns_name(self,
                                                    mock_boto_client):

            mock_boto_client.describe_instances.return_value = {
                    "Reservations": [
                        {
                            "Instances": [
                                {
                                    "AmiLaunchIndex": 0,
                                    "ImageId": "ami-0551d1417af39acc9",
                                    "InstanceId": "i-0212daed6389691d3",
                                    "Placement": {
                                        "AvailabilityZone": "eu-west-2a",
                                        "GroupName": "",
                                        "Tenancy": "default"
                                    },
                                    "PrivateDnsName": "ip-10-250-3-14.eu-west-2.compute.internal",
                                    "PrivateIpAddress": "10.250.3.14",
                                    "ProductCodes": [

                                    ],
                                    "PublicDnsName": "",
                                    "State": {
                                        "Code": 16,
                                        "Name": "running"
                                    },
                                    "SubnetId": "subnet-82a5c1f9",
                                    "VpcId": "vpc-da3c49b3",
                                    "LaunchTime": self.notifier.current_timestamp,
                                    "Tags": [
                                        {
                                            "Key": "Name",
                                            "Value": "test"
                                        },
                                        {
                                            "Key": "Env",
                                            "Value": "test"
                                        },
                                        {
                                            "Key": "AcpSHA",
                                            "Value": "a5adc91a3deb7d07a351d89b003fa779d5106df7"
                                        },
                                        {
                                            "Key": "KubernetesCluster",
                                            "Value": "test.testing.acp.homeoffice.gov.uk"
                                        }
                                    ],
                                }
                            ],
                            "OwnerId": "670930646103",
                            "RequesterId": "626974355284",
                            "ReservationId": "r-00a8bee9bfdda697a"
                        }
                    ]
                }

            instance = self.notifier.get_instance_from_private_dns_name('a', mock_boto_client)

            self.assertTrue(instance['launch_time'] == self.notifier.current_timestamp,
                            instance['name'] == 'test')

            mock_boto_client.describe_instances.assert_called_once()




