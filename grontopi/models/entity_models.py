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




class AbbreviatedProvenance(BaseModel):
    soporte_documental: DocumentURI
    validity_period: Optional[UndeterminedTimeInterval]


class GeneralProvenanceInfo(BaseModel):
    soporte_documental: DocumentURI
    anotacion: Optional[AnnotationURI]
    annotation_date: Optional[datetime.date]
    is_valid: Optional[bool]
    reification_uri: Optional[ReificationURI]




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
