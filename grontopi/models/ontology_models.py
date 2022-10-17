from pydantic import AnyUrl, UrlError, errors, BaseModel
from typing import Dict, List, Optional



class NotExisting(UrlError):
    code = "uri.nonexisting"
    msg_template = "given uri does not exist"


class WrappedUri(AnyUrl):
    @classmethod
    def validate(cls, *args, **kwargs) -> AnyUrl:
        if "value" in kwargs.keys():
            value = kwargs["value"].strip()
        else:
            value = args[0]
        if len(value) < 4 or type(value) is not str:
            raise errors.StrError()
        if value[0] != "<" or value[-1] != ">":
            e = errors.StrError()
            e.msg_template = "URIs should have pointy brackets around them "
            raise e
        return super().validate(value=value[1:-1],
                                field=kwargs["field"],
                                config=kwargs["config"])

    def build(
            cls,
            *args,
            **kwargs: str,
    ) -> str:
        return "<" + super().build(*args, **kwargs) + ">"

    def __new__(cls, url: str, **kwargs) -> object:
        if url is None:
            r = cls.build(**kwargs)
        else:
            r = url
        if r[0] != "<" and r[-1] != ">":
            r = "<" + r + ">"
        return str.__new__(cls, r)


# ToDo implement further checks on these URIs

class ClassURI(WrappedUri):
    @classmethod
    def validate(cls, *args, **kwargs) -> AnyUrl:
        value = args[0]
        return super().validate(value=value,
                                field=kwargs["field"],
                                config=kwargs["config"])


class PropertyURI(WrappedUri):
    @classmethod
    def validate(cls, *args, **kwargs) -> AnyUrl:
        value = args[0]
        return super().validate(value=value,
                                field=kwargs["field"],
                                config=kwargs["config"])


class RelationURI(WrappedUri):
    @classmethod
    def validate(cls, *args, **kwargs) -> AnyUrl:
        value = args[0]
        return super().validate(value=value,
                                field=kwargs["field"],
                                config=kwargs["config"])


class ReificationURI(WrappedUri):
    @classmethod
    def validate(cls, *args, **kwargs) -> AnyUrl:
        value = args[0]
        return super().validate(value=value,
                                field=kwargs["field"],
                                config=kwargs["config"])


class EntityURI(WrappedUri):
    @classmethod
    def validate(cls, *args, **kwargs) -> AnyUrl:
        value = args[0]
        return super().validate(value=value,
                                field=kwargs["field"],
                                config=kwargs["config"])

    class Config:
        schema_extra = {
            "example": "<https://entities.graph/people/X_61f2a4>"}


class DocumentURI(WrappedUri):
    @classmethod
    def validate(cls, *args, **kwargs) -> AnyUrl:
        value = args[0]
        return super().validate(value=value,
                                field=kwargs["field"],
                                config=kwargs["config"])


class AnnotationURI(WrappedUri):
    @classmethod
    def validate(cls, *args, **kwargs) -> AnyUrl:
        value = args[0]
        return super().validate(value=value,
                                field=kwargs["field"],
                                config=kwargs["config"])


class CatalogURI(WrappedUri):
    @classmethod
    def validate(cls, *args, **kwargs) -> AnyUrl:
        value = args[0]
        return super().validate(value=value,
                                field=kwargs["field"],
                                config=kwargs["config"])


class RoleURI(WrappedUri):
    @classmethod
    def validate(cls, *args, **kwargs) -> AnyUrl:
        value = args[0]
        return super().validate(value=value,
                                field=kwargs["field"],
                                config=kwargs["config"])


class MentionURI(WrappedUri):
    @classmethod
    def validate(cls, *args, **kwargs) -> AnyUrl:
        value = args[0]
        return super().validate(value=value,
                                field=kwargs["field"],
                                config=kwargs["config"])


class ClassDescription(BaseModel):
    label: List[str]
    subclasses: List[ClassURI]
    isRangeOf: Optional[List[RelationURI]]
    isDomainOf: Optional[List[RelationURI]]


class RelationDescription(BaseModel):
    label: List[str]
    default_label: str
    domain: List[ClassURI]
    range: List[ClassURI]
    rangetype: Optional[str]


class CondensedOntology(BaseModel):
    catalogs: Dict
    classes: Dict[ClassURI, ClassDescription]
    relations: Dict[RelationURI, RelationDescription]
    props: Dict[PropertyURI, RelationDescription]
