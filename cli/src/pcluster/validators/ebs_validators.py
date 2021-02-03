# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "LICENSE.txt" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions and
# limitations under the License.
from botocore.exceptions import ClientError

from pcluster.config.validators import (
    EBS_VOLUME_IOPS_BOUNDS,
    EBS_VOLUME_TYPE_TO_IOPS_RATIO,
    EBS_VOLUME_TYPE_TO_VOLUME_SIZE_BOUNDS,
)
from pcluster.models.common import FailureLevel, Param, Validator
from pcluster.utils import get_ebs_snapshot_info, get_partition


class EbsVolumeTypeSizeValidator(Validator):
    """EBS volume type and size validator.

    Validate that the EBS volume size matches the chosen volume type.

    The default value of volume_size for EBS volumes is 20 GiB.
    The volume size of standard ranges from 1 GiB - 1 TiB(1024 GiB)
    The volume size of gp2 and gp3 ranges from 1 GiB - 16 TiB(16384 GiB)
    The volume size of io1 and io2 ranges from 4 GiB - 16 TiB(16384 GiB)
    The volume sizes of st1 and sc1 range from 500 GiB - 16 TiB(16384 GiB)
    """

    def _validate(self, volume_type: Param, volume_size: Param):
        if volume_type.value in EBS_VOLUME_TYPE_TO_VOLUME_SIZE_BOUNDS:
            min_size, max_size = EBS_VOLUME_TYPE_TO_VOLUME_SIZE_BOUNDS.get(volume_type.value)
            if volume_size.value > max_size:
                self._add_failure(
                    "The size of {0} volumes can not exceed {1} GiB".format(volume_type.value, max_size),
                    FailureLevel.ERROR,
                    [volume_size],
                )
            elif volume_size.value < min_size:
                self._add_failure(
                    "The size of {0} volumes must be at least {1} GiB".format(volume_type.value, min_size),
                    FailureLevel.ERROR,
                    [volume_size],
                )


class EbsVolumeThroughputValidator(Validator):
    """
    EBS volume throughput validator.

    Validate gp3 throughput.
    """

    def _validate(self, volume_type: Param, volume_throughput: Param):
        if volume_type.value == "gp3":
            min_throughput, max_throughput = 125, 1000
            if volume_throughput.value < min_throughput or volume_throughput.value > max_throughput:
                self._add_failure(
                    "Throughput must be between {min_throughput} MB/s and {max_throughput} MB/s when provisioning "
                    "{volume_type} volumes.".format(
                        min_throughput=min_throughput, max_throughput=max_throughput, volume_type=volume_type.value
                    ),
                    FailureLevel.ERROR,
                    [volume_throughput],
                )


class EbsVolumeThroughputIopsValidator(Validator):
    """
    EBS volume throughput to iops ratio validator.

    Validate gp3 throughput.
    """

    def _validate(self, volume_type: Param, volume_iops: Param, volume_throughput: Param):
        volume_throughput_to_iops_ratio = 0.25
        if volume_type.value == "gp3":
            if (
                volume_throughput.value
                and volume_throughput.value > volume_iops.value * volume_throughput_to_iops_ratio
            ):
                self._add_failure(
                    "Throughput to IOPS ratio of {0} is too high; maximum is 0.25.".format(
                        float(volume_throughput.value) / float(volume_iops.value)
                    ),
                    FailureLevel.ERROR,
                    [volume_throughput],
                )


class EbsVolumeIopsValidator(Validator):
    """
    EBS volume IOPS validator.

    Validate IOPS value in respect of volume type.
    """

    def _validate(self, volume_type: Param, volume_size: Param, volume_iops: Param):
        if volume_type.value in EBS_VOLUME_IOPS_BOUNDS:
            min_iops, max_iops = EBS_VOLUME_IOPS_BOUNDS.get(volume_type.value)
            if volume_iops.value and (volume_iops.value < min_iops or volume_iops.value > max_iops):
                self._add_failure(
                    f"IOPS rate must be between {min_iops} and {max_iops}"
                    f" when provisioning {volume_type.value} volumes.",
                    FailureLevel.ERROR,
                    [volume_iops],
                )
            elif (
                volume_iops.value
                and volume_iops.value > volume_size.value * EBS_VOLUME_TYPE_TO_IOPS_RATIO[volume_type.value]
            ):
                self._add_failure(
                    "IOPS to volume size ratio of {0} is too high; maximum is {1}.".format(
                        float(volume_iops.value) / float(volume_size.value),
                        EBS_VOLUME_TYPE_TO_IOPS_RATIO[volume_type.value],
                    ),
                    FailureLevel.ERROR,
                    [volume_iops],
                )


class EbsVolumeSizeSnapshotValidator(Validator):
    """
    EBS volume size snapshot validator.

    Validate the following cases:
    - The EBS snapshot is in "completed" state if it is specified.
    - If users specify the volume size, the volume must be not smaller than the volume size of the EBS snapshot.
    """

    def _validate(self, snapshot_id: Param, volume_size: Param):
        if snapshot_id.value:
            try:
                snapshot_response_dict = get_ebs_snapshot_info(snapshot_id.value, raise_exceptions=True)

                # validate that the input volume size is larger than the volume size of the EBS snapshot
                snapshot_volume_size = snapshot_response_dict.get("VolumeSize")
                if snapshot_volume_size is None:
                    self._add_failure(
                        f"Unable to get volume size for snapshot {snapshot_id.value}", FailureLevel.ERROR, [snapshot_id]
                    )
                elif volume_size.value < snapshot_volume_size:
                    self._add_failure(
                        f"The EBS volume size must not be smaller than {snapshot_volume_size}, "
                        "because it is the size of the provided snapshot {snapshot_id}",
                        FailureLevel.ERROR,
                        [volume_size],
                    )
                elif volume_size.value > snapshot_volume_size:
                    self._add_failure(
                        "The specified volume size is larger than snapshot size. In order to use the full capacity "
                        "of the volume, you'll need to manually resize the partition according to this doc: "
                        "https://{partition_url}/AWSEC2/latest/UserGuide/recognize-expanded-volume-linux.html".format(
                            partition_url="docs.amazonaws.cn" if get_partition() == "aws-cn" else "docs.aws.amazon.com"
                        ),
                        FailureLevel.WARNING,
                        [volume_size],
                    )

                # validate that the state of ebs snapshot
                if snapshot_response_dict.get("State") != "completed":
                    self._add_failure(
                        "Snapshot {0} is in state '{1}' not 'completed'".format(
                            snapshot_id.value, snapshot_response_dict.get("State")
                        ),
                        FailureLevel.WARNING,
                        [snapshot_id],
                    )
            except Exception as exception:
                if isinstance(exception, ClientError) and exception.response.get("Error").get("Code") in [
                    "InvalidSnapshot.NotFound",
                    "InvalidSnapshot.Malformed",
                ]:
                    self._add_failure(
                        "The snapshot {0} does not appear to exist: {1}".format(
                            snapshot_id.value, exception.response.get("Error").get("Message")
                        ),
                        FailureLevel.ERROR,
                        [snapshot_id],
                    )
                else:
                    self._add_failure(
                        "Issue getting info for snapshot {0}: {1}".format(
                            snapshot_id.value,
                            exception.response.get("Error").get("Message")
                            if isinstance(exception, ClientError)
                            else exception,
                        ),
                        FailureLevel.ERROR,
                        [snapshot_id],
                    )


class EBSVolumeKmsKeyIdValidator(Validator):
    """
    EBS volume KmsKeyId validator.

    Validate KmsKeyId value based on encrypted value.
    """

    def _validate(self, volume_kms_key_id: Param, volume_encrypted: Param):
        if volume_kms_key_id.value and not volume_encrypted.value:
            self._add_failure(
                "Kms Key Id {0} is specified, the encrypted state must be True.".format(volume_kms_key_id.value),
                FailureLevel.ERROR,
                [volume_encrypted],
            )