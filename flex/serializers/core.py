from __future__ import unicode_literals

import collections
import six

from rest_framework import serializers

from drf_compound_fields.fields import ListField

from flex.serializers.fields import (
    SecurityRequirementReferenceField,
)
from flex.serializers.mixins import (
    TypedDefaultMixin,
)
from flex.serializers.common import (
    HomogenousDictSerializer,
    CommonJSONSchemaSerializer,
    BaseResponseSerializer,
    BaseParameterSerializer,
    BaseSchemaSerializer,
    BaseItemsSerializer,
)
from flex.serializers.validators import (
    host_validator,
    path_validator,
    scheme_validator,
    mimetype_validator,
    string_type_validator,
    header_type_validator,
    format_validator,
    collection_format_validator,
)
from flex.constants import (
    CSV,
    ARRAY,
)


class InfoSerializer(serializers.Serializer):
    """
    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#infoObject
    """
    title = serializers.CharField()
    description = serializers.CharField(required=False)
    termsOfService = serializers.CharField(required=False)
    contact = serializers.CharField(required=False)
    license = serializers.CharField(required=False)
    version = serializers.CharField(required=False)


class ItemsSerializer(BaseItemsSerializer):
    pass


class HeaderSerializer(TypedDefaultMixin, CommonJSONSchemaSerializer):
    """
    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#header-object-
    """
    default_error_messages = {
        'items_required': (
            "When type is \"array\" the \"items\" is required"
        ),
    }
    description = serializers.CharField(required=False)
    type = serializers.CharField(validators=[header_type_validator])
    format = serializers.CharField(validators=[format_validator], required=False)
    items = ItemsSerializer(required=False, many=True)
    collectionFormat = serializers.CharField(
        required=False, validators=[collection_format_validator], default=CSV,
    )
    default = serializers.WritableField(required=False)

    def validate(self, attrs):
        errors = collections.defaultdict(list)
        if attrs.get('type') == ARRAY and 'items' not in attrs:
            errors['items'].append(
                self.error_messages['items_required'],
            )
        self.validate_default_type(attrs, errors)

        if errors:
            raise serializers.ValidationError(errors)
        return super(HeaderSerializer, self).validate(attrs)


class HeadersSerializer(HomogenousDictSerializer):
    """
    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#headersObject
    """
    value_serializer_class = HeaderSerializer


class SchemaSerializer(BaseSchemaSerializer):
    pass


class ResponseSerializer(BaseResponseSerializer):
    """
    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#responseObject
    """
    description = serializers.CharField()
    schema = SchemaSerializer(required=False)
    headers = HeadersSerializer(required=False)
    # TODO: how do we do examples
    # examples =


class ResponsesSerializer(HomogenousDictSerializer):
    value_serializer_class = ResponseSerializer


class SecuritySerializer(HomogenousDictSerializer):
    value_serializer_class = SecurityRequirementReferenceField


class ParameterSerializer(BaseParameterSerializer):
    default_error_messages = {
        'unknown_reference': "Unknown reference `{0}`",
    }

    schema = SchemaSerializer(required=False)
    items = ItemsSerializer(required=False, many=True)

    def from_native(self, data, files=None):
        if isinstance(data, six.string_types):
            try:
                self.validate_reference(data)
            except serializers.ValidationError as err:
                assert not self._errors
                self._errors = {}
                self._errors['non_field_errors'] = self._errors.get(
                    'non_field_errors', [],
                ) + list(err.messages)
                return
            else:
                return data
        return super(BaseParameterSerializer, self).from_native(data, files)

    def validate_reference(self, reference):
        if reference not in self.context.get('parameters', {}):
            raise serializers.ValidationError(
                self.error_messages['unknown_reference'].format(reference),
            )


class OperationSerializer(serializers.Serializer):
    """
    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#operationObject
    """
    tags = ListField(required=False, validators=[string_type_validator])
    summary = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    externalDocs = serializers.CharField(required=False)
    operationId = serializers.CharField(required=False)
    consumes = ListField(required=False, validators=[mimetype_validator])
    produces = ListField(required=False, validators=[mimetype_validator])
    parameters = ParameterSerializer(required=False, many=True)
    responses = ResponsesSerializer()
    schemes = ListField(required=False, validators=[scheme_validator])
    deprecated = serializers.BooleanField(required=False)
    security = SecuritySerializer(required=False)


class PathItemSerializer(serializers.Serializer):
    """
    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#pathsObject
    """
    # TODO. reference path item objects from definitions.
    # TODO. how is this supposted to work.  The swagger spec doesn't account
    # for a definitions location for PathItem definitions?
    # _ref = serializers.CharField(source='$ref')
    get = OperationSerializer(required=False)
    put = OperationSerializer(required=False)
    post = OperationSerializer(required=False)
    delete = OperationSerializer(required=False)
    options = OperationSerializer(required=False)
    head = OperationSerializer(required=False)
    patch = OperationSerializer(required=False)
    # TODO: these can be a parameters reference object.
    parameters = ParameterSerializer(required=False, many=True)


class TagSerializer(serializers.Serializer):
    """
    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#tagObject
    """
    name = serializers.CharField()
    description = serializers.CharField(required=False)
    externalDocs = serializers.CharField(required=False)


class PropertiesSerializer(HomogenousDictSerializer):
    value_serializer_class = SchemaSerializer


# These fields include recursive use of the `SchemaSerializer` so they have to
# be attached after the `SchemaSerializer` class has been created.
SchemaSerializer.base_fields['properties'] = PropertiesSerializer(required=False)
SchemaSerializer.base_fields['items'] = ItemsSerializer(required=False, many=True)
SchemaSerializer.base_fields['allOf'] = SchemaSerializer(required=False, many=True)


class PathsSerializer(HomogenousDictSerializer):
    value_serializer_class = PathItemSerializer


class SwaggerSerializer(serializers.Serializer):
    """
    Primary Serializer for swagger schema
    """
    swagger = serializers.ChoiceField(
        choices=[('2.0', '2.0')],
    )
    info = InfoSerializer()
    host = serializers.CharField(
        required=False,
        validators=[host_validator],
    )
    basePath = serializers.CharField(
        required=False,
        validators=[path_validator],
    )
    schemes = ListField(required=False, validators=[scheme_validator])
    consumes = ListField(required=False, validators=[mimetype_validator])
    produces = ListField(required=False, validators=[mimetype_validator])

    paths = PathsSerializer()

    security = SecuritySerializer(required=False)

    tags = TagSerializer(required=False, many=True)
    externalDocs = serializers.CharField(required=False)