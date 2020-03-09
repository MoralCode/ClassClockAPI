"""
Customized Marshmallow-SQLAlchemy and Marshmallow-JSONAPI Schemas to combine Schema Meta data.
"""
import marshmallow as ma
import marshmallow_jsonapi
import marshmallow_sqlalchemy

from common.helpers import camel_to_delimiter_separated
from common.db_schema import db

from .convert import ModelConverter
from .exceptions import ForbiddenIdError, MismatchIdError, NullPrimaryData
from .fields import MetaData
from common.db_schema import BellSchedule, BellScheduleMeetingTime, School


# this is literally the most important part of how this API works
# it basically combines marshmallow_sqlalchemy and marshmallow_jsonapi
# allowing BOTH autogeneration of marshmallow schemas from SQLAlchemy
# models, AND serializing those schemas to a JSONAPI 1.0 compatible format
# thank you to the gods of coding at https://stackoverflow.com/a/53035144
def make_jsonapi_schema_class(model_class):

    # https://marshmallow-sqlalchemy.readthedocs.io/en/latest/recipes.html#automatically-generating-schemas-for-sqlalchemy-models
    class Meta:
        # Marshmallow-SQLAlchemy
        model = model_class
        sqla_session = db.session

        # Marshmallow-JSONAPI
        type_ = model_class.__name__.lower()
        self_view = type_ + '_detail'
        self_view_kwargs = {'id': '<id>'}
        self_view_many = type_ + '_list'

    schema_class = type(model_class.__name__ + 'Schema',
                        (Schema,), {'Meta': Meta})
    return schema_class

    
class SchemaOpts(marshmallow_jsonapi.SchemaOpts, marshmallow_sqlalchemy.ModelSchemaOpts):  # pylint: disable=too-few-public-methods
    """ Combine JSON API Schema Opts with SQLAlchemy Schema Opts.
    This fixes the error: AttributeError: 'SchemaOpts' object has no attribute 'model_converter """

    def __init__(self, meta, *args, **kwargs):
        """
        Forces strict=True.
        Forces type_ to kebab-case of self.opts.model.__name__ for JSONAPI recommendation.
        Sets up default self_url and kwargs if model option is set.
        Sets up default self_url_many if model and listable are truthy.
        """
        # Does Resource support a read list endpoint? Default False. Needed for Swagger.
        self.listable = getattr(meta, 'listable', False)

        # TODO: ROB 20170726 Check status of github.com/marshmallow-code/marshmallow/issues/377
        # Force strict by default until ticket is resolved.
        meta.strict = True

        # When the base Schema below is first initialized there won't be a model element.
        model = getattr(meta, 'model', None)
        if model:
            # Automatically set the JSONAPI type (marshmallow-jsonapi) based on model name.
            # JSONAPI recommends kebab-case for naming: http://jsonapi.org/recommendations/#naming
            type_ = camel_to_delimiter_separated(
                model.__name__, glue='-')
            meta.type_ = type_

            # Self URLs are always based on the JSONAPI type and the model id
            meta.self_url = f'/{type_}/{{id}}'
            meta.self_url_kwargs = {'id': '<id>'}
            # Always include the many url for resource creation at least
            meta.self_url_many = f'/{type_}s'

        # Use our custom ModelConverter to turn SQLAlchemy relations into JSONAPI Relationships.
        meta.model_converter = ModelConverter

        def dasherize(text):
            """
            Convert snake_case field names to jsonapi kebab-case.
            :param str text: field name
            :return str: kebab-case name
            """
            return text.replace('_', '-')
        meta.inflect = dasherize

        super().__init__(meta, *args, **kwargs)


class Schema(marshmallow_jsonapi.Schema, marshmallow_sqlalchemy.ModelSchema):
    """ Set custom options class to combine JSONAPI and SQLAlchemy. Set strict option by default.
    Configure DB connection on init. """
    OPTIONS_CLASS = SchemaOpts

    # id must be a string: http://jsonapi.org/format/#document-resource-object-identification
    id = marshmallow_jsonapi.fields.String(length=16)  # pylint: disable=invalid-name
    # This field is read only, place in meta data: http://jsonapi.org/format/#document-meta
    modified_at = MetaData(marshmallow_jsonapi.fields.DateTime())

    def __init__(self, *args, **kwargs):
        """
        Combine the inits for marshmallow_jsonapi.Schema, marshmallow_sqlalchemy.ModelSchema.
        Forces session=db.connect().
        """
        # control if unwrap_item checks for the id field in the object.
        self.load_existing = True

        # Each instance of the schema should have the current session with the DB
        # (marshmallow-sqlschema). This must be done on instance init, not on class creation!

        # kwargs['session'] = db.connect()

        super().__init__(*args, **kwargs)

    @classmethod
    def field_for(cls, field_name):
        """
        Get a marshmallow field object for an attribute of this schema.
        :param str field_name: Name of attribute to return the marshmallow.fields for.
        :return ourmarshmallow.fields.Field: Subclass of Field for attribute of schema class.
        """
        # _declared_fields is set by the metaclass marshmallow.schema.SchemaMeta
        ret = cls._declared_fields[field_name]  # pylint: disable=no-member
        # ret._add_to_schema(field_name, cls)
        return ret

    @ma.post_load(pass_many=True)
    def make_instance(self, data, many):  # pylint: disable=arguments-differ
        """
        Deserialize data to instances of the model. Update an existing if specified in
        `self.instance` or loaded by primary key(s) in the data; else create a new model.
        :param data: Data to deserialize.
        :param many: Does data represent many models.
        :return models.BaseModel or list(models.BaseModel): Instance(s) of model(s) updated with
                                                            data.
        """
        if many:
            return [super().make_instance(each) for each in data]
        return super().make_instance(data)

    def unwrap_item(self, item):
        """
        If the schema has an existing instance the id field must be set.
        :raises ValidationError: id field isn't present when required.
        """
        id_in_item = 'id' in item
        if self.load_existing and not id_in_item:
            # Updating Resources must include type and id keys
            # http://jsonapi.org/format/1.1/#crud-updating
            raise ma.ValidationError([{'detail': '`data` object must include `id` key.',
                                       'source': {'pointer': '/data'}}])

        if not self.load_existing and id_in_item:
            # Don't support client side identifier generation at this time.
            raise ForbiddenIdError()

        return super().unwrap_item(item)

    @ma.pre_load(pass_many=True)
    def unwrap_request(self, data, many):
        if 'data' not in data:
            raise ma.ValidationError('Object must include `data` key.')

        data = data['data']
        data_is_collection = ma.utils.is_collection(data)
        if many:
            if not data_is_collection:
                raise ma.ValidationError([{'detail': '`data` object must be a collection.',
                                           'source': {'pointer': '/data'}}])

            return [self.unwrap_item(each) for each in data]

        if data_is_collection:
            raise ma.ValidationError([
                {'detail': '`data` object must be an object, not a collection.',
                 'source': {'pointer': '/data'}}])

        if data is None:
            # When updating relationships we need to specially handle the primary data being null.
            # http://jsonapi.org/format/1.1/#crud-updating-to-one-relationships
            raise NullPrimaryData()

        return self.unwrap_item(data)

    @ma.validates('id')
    def validate_id(self, value):
        """
        If the schema has an existing instance the id value must match id. Use custom errors so we
        can generate to the correct source.pointer and response code.
        :param int value: identifier from payload.
        :raises MismatchIdError: id field doesn't match self.instance.
        """
        if self.instance and self.instance.id != value:
            raise MismatchIdError(actual=value, expected=self.instance.id)


SchoolSchema = make_jsonapi_schema_class(School)
BellScheduleSchema = make_jsonapi_schema_class(BellSchedule)
ClassPeriodSchema = make_jsonapi_schema_class(BellScheduleMeetingTime)
