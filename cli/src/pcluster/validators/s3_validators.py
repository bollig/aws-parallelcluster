import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import urlopen

from botocore.exceptions import ClientError

from common.boto3.s3 import S3Client
from pcluster.models.common import FailureLevel, Param, Validator


class UrlValidator(Validator):
    """
    Url Validator.

    Validate given url with s3, https or file prefix.
    """

    def _validate(self, url: Param):
        scheme = urlparse(url.value).scheme
        if scheme in ["https", "s3", "file"]:
            if scheme == "s3":
                self._validate_s3_uri(url.value)
            if scheme == "https":
                try:
                    urlopen(url.value)
                except HTTPError as e:
                    self._add_failure(
                        "The url '{0}' cause HTTPError, the error code is '{1}', the error reason is '{2}'".format(
                            url.value, e.code, e.reason
                        ),
                        FailureLevel.WARNING,
                    )
                except URLError as e:
                    self._add_failure(
                        "The url '{0}' causes URLError, the error reason is '{1}'".format(url.value, e.reason),
                        FailureLevel.WARNING,
                    )
                except ValueError:
                    self._add_failure(
                        "The value '{0}' is not a valid URL".format(url.value),
                        FailureLevel.ERROR,
                        [url],
                    )
        else:
            self._add_failure(
                f"The value '{url.value}' is not a valid URL, choose URL with 'https', 's3' or 'file' prefix.",
                FailureLevel.ERROR,
                [url],
            )

    def _validate_s3_uri(self, s3_url):
        try:
            match = re.match(r"s3://(.*?)/(.*)", s3_url)
            if not match or len(match.groups()) < 2:
                self._add_failure(f"s3 url '{s3_url}' is invalid.", FailureLevel.ERROR)
            bucket_name, object_name = match.group(1), match.group(2)
            S3Client().head_object(bucket_name=bucket_name, object_name=object_name)

        except ClientError:
            # Todo: Check that bucket is in s3_read_resource or s3_read_write_resource.
            self._add_failure(
                (
                    "The S3 object does not exist or you do not have access to it.\n"
                    "Please make sure the cluster nodes have access to it."
                ),
                FailureLevel.ERROR,
            )