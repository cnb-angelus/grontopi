import datetime
from datetime import date
from typing import List, Optional, Union

from pydantic import BaseModel

from models.catalog_models import Confianza, MetodoInferencia
from models.ontology_models import AnnotationURI, EntityURI
from models.ontology_models import ClassURI
from models.ontology_models import ReificationURI, DocumentURI
from models.ontology_models import WrappedUri, RelationURI


class UndeterminedTimeInterval(BaseModel):
    start_date_lower_bound: Optional[date]
    start_date_upper_bound: Optional[date]
    end_date_lower_bound: Optional[date]
    end_date_upper_bound: Optional[date]


class SpecificProvenanceInfo(BaseModel):
    observaciones: Optional[str]
    confianza: Optional[Confianza]
    metodo_inferencia: Optional[MetodoInferencia]
    validity_period: Optional[UndeterminedTimeInterval]

    class Config:
        schema_extra = {
            "example": {
                "observaciones": "Observaciones sobre relación entre Don "
                                 "Fulanito y La Organización X",
                "confianza": "<https://vocabs.graph/v1.0/Confianza/Alta>",
                "metodo_inferencia": "<https://vocabs.graph/Inf/Autómático>"
            },
        }
        description = "Provenance info about a statement or entity"
        title = "Specific Proveance Info"


class AbbreviatedProvenance(BaseModel):
    soporte_documental: DocumentURI
    validity_period: Optional[UndeterminedTimeInterval]


class GeneralProvenanceInfo(BaseModel):
    soporte_documental: DocumentURI
    anotacion: Optional[AnnotationURI]
    annotation_date: Optional[datetime.date]
    is_valid: Optional[bool]
    reification_uri: Optional[ReificationURI]

    class Config:
        schema_extra = {
            "example": {
                "soporte_documental": "<https://docs.graph/documentos/doc1>",
                "annotation_date": "2020-09-16",
                "polygon": {
                    "upper_left_x": 1000,
                    "upper_left_y": 1000,
                    "lower_right_x": 1012,
                    "lower_right_y": 1016,
                    "hex_color": "#00FF00"
                }
            }
        }
        description = """Provenance info linking an annotation to the real
                      world document containing it"""
        title = "General Proveance Info"


class LabelWithLang(BaseModel):
    label_predicate: str
    label_value: str
    label_lang: Optional[str]


class PredicateLiteralTuple(BaseModel):
    predicate: RelationURI
    literal: Union[int,
                   float,
                   datetime.datetime,
                   datetime.date,
                   str]
    specific_provenance: Optional[SpecificProvenanceInfo]
    provenance: Optional[GeneralProvenanceInfo]


class EntityWithLabel(BaseModel):
    entity: EntityURI
    labels: Optional[List[LabelWithLang]]
    longname: Optional[str]
    class_id: Optional[ClassURI]
    other_classes: Optional[List[ClassURI]]


class PredicateObjectTuple(BaseModel):
    predicate: RelationURI
    object: EntityURI
    specific_provenance: Optional[SpecificProvenanceInfo]
    object_labels: Optional[List[LabelWithLang]]
    provenance: Optional[GeneralProvenanceInfo]
