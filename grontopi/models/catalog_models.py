from pydantic import AnyUrl

from models.ontology_models import WrappedUri


class Confianza(WrappedUri):
    @classmethod
    def validate(cls, *args, **kwargs) -> 'AnyUrl':
        value = args[0]
        return super().validate(value=value,
                                field=kwargs["field"],
                                config=kwargs["config"])


class MetodoInferencia(WrappedUri):
    @classmethod
    def validate(cls, *args, **kwargs) -> 'AnyUrl':
        value = args[0]
        return super().validate(value=value,
                                field=kwargs["field"],
                                config=kwargs["config"])
