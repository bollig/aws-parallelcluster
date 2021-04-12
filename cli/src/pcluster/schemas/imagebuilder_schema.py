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

#
# This module contains all the classes representing the Schema of the configuration file.
# These classes are created by following marshmallow syntax.
#
import re

from marshmallow import ValidationError, fields, post_load, validate, validates, validates_schema

from common.utils import get_url_scheme, validate_json_format
from pcluster.models.imagebuilder_config import (
    Build,
    Component,
    DistributionConfiguration,
    Iam,
    Image,
    ImageBuilderConfig,
    ImagebuilderDevSettings,
    Volume,
)
from pcluster.schemas.common_schema import (
    ALLOWED_VALUES,
    BaseDevSettingsSchema,
    BaseSchema,
    TagSchema,
    get_field_validator,
)

# ---------------------- Image Schema---------------------- #


class VolumeSchema(BaseSchema):
    """Represent the schema of the ImageBuilder Volume."""

    size = fields.Int()
    encrypted = fields.Bool()
    kms_key_id = fields.Str()

    @post_load()
    def make_resource(self, data, **kwargs):
        """Generate resource."""
        return Volume(**data)


class ImageSchema(BaseSchema):
    """Represent the schema of the ImageBuilder Image."""

    tags = fields.List(fields.Nested(TagSchema))
    root_volume = fields.Nested(VolumeSchema)

    @post_load
    def make_resource(self, data, **kwargs):
        """Generate resource."""
        return Image(**data)

    @validates("tags")
    def validate_reserved_tag(self, value):
        """Validate reserved tag in tags."""
        if value:
            for tag in value:
                match = re.match(r"^pcluster_*", tag.key)
                if match:
                    raise ValidationError(message="The tag key prefix 'pcluster_' is reserved and cannot be used.")


# ---------------------- Build Schema---------------------- #


class ComponentSchema(BaseSchema):
    """Represent the schema of the ImageBuilder component."""

    type = fields.Str(validate=validate.OneOf(["arn", "script"]))
    value = fields.Str()

    @post_load()
    def make_resource(self, data, **kwargs):
        """Generate resource."""
        return Component(**data)

    @validates_schema()
    def validate_component_value(self, data, **kwargs):
        """Validate component value format."""
        type = data.get("type")
        value = data.get("value")
        if type == "arn" and not value.startswith("arn"):
            raise ValidationError(
                message="The Type in Component is arn, the value '{0}' is invalid. "
                "Choose a value with 'arn' prefix.".format(value),
                field_name="Value",
            )
        if type == "script" and get_url_scheme(value) not in ["https", "s3"]:
            raise ValidationError(
                message="The Type in Component is script, the value '{0}' is invalid. "
                "Choose a value with 'https' or 's3' prefix url.".format(value),
                field_name="Value",
            )


class DistributionConfigurationSchema(BaseSchema):
    """Represent the schema of the ImageBuilder distribution configuration."""

    regions = fields.Str()
    launch_permission = fields.Str()

    @post_load()
    def make_resource(self, data, **kwargs):
        """Generate resource."""
        return DistributionConfiguration(**data)

    @validates("launch_permission")
    def validate_launch_permission(self, value):
        """Validate json."""
        if value and not validate_json_format(value):
            raise ValidationError(message="'{0}' is invalid".format(value))


class IamSchema(BaseSchema):
    """Represent the schema of the ImageBuilder IAM."""

    instance_role = fields.Str(validate=validate.Regexp("^arn:.*:(role|instance-profile)/"))
    cleanup_lambda_role = fields.Str(validate=validate.Regexp("^arn:.*:role/"))

    @post_load()
    def make_resource(self, data, **kwargs):
        """Generate resource."""
        return Iam(**data)


class BuildSchema(BaseSchema):
    """Represent the schema of the ImageBuilder Build."""

    iam = fields.Nested(IamSchema)
    instance_type = fields.Str(required=True)
    components = fields.List(fields.Nested(ComponentSchema))
    parent_image = fields.Str(required=True, validate=validate.Regexp("^ami|arn"))
    tags = fields.List(fields.Nested(TagSchema))
    security_group_ids = fields.List(fields.Str)
    subnet_id = fields.Str(validate=get_field_validator("subnet_id"))

    @post_load
    def make_resource(self, data, **kwargs):
        """Generate resource."""
        return Build(**data)

    @validates("security_group_ids")
    def validate_security_group_ids(self, value):
        """Validate security group ids."""
        if value and not all(
            re.match(ALLOWED_VALUES["security_group_id"], security_group_id) for security_group_id in value
        ):
            raise ValidationError(message="The SecurityGroupIds contains invalid security group id.")


# ---------------------- Dev Settings Schema ---------------------- #


class ImagebuilderDevSettingsSchema(BaseDevSettingsSchema):
    """Represent the schema of the ImageBuilder Dev Setting."""

    update_os_and_reboot = fields.Bool()
    disable_pcluster_component = fields.Bool()
    distribution_configuration = fields.Nested(DistributionConfigurationSchema)
    terminate_instance_on_failure = fields.Bool()

    @post_load
    def make_resource(self, data, **kwargs):
        """Generate resource."""
        return ImagebuilderDevSettings(**data)


# ---------------------- ImageBuilder Schema ---------------------- #


class ImageBuilderSchema(BaseSchema):
    """Represent the schema of the ImageBuilder."""

    image = fields.Nested(ImageSchema)
    build = fields.Nested(BuildSchema, required=True)
    dev_settings = fields.Nested(ImagebuilderDevSettingsSchema)
    custom_s3_bucket = fields.Str()

    @post_load(pass_original=True)
    def make_resource(self, data, original_data, **kwargs):
        """Generate resource."""
        return ImageBuilderConfig(source_config=original_data, **data)