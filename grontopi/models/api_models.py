from typing import List, Optional

from pydantic import BaseModel

from models.entity_models import LabelWithLang, EntityWithLabel
from models.entity_models import PredicateLiteralTuple, \
    PredicateObjectTuple, AbbreviatedProvenance
from models.ontology_models import EntityURI, ClassURI, \
    RelationURI, ReificationURI, RoleURI


class EntityListWithLabels(BaseModel):
    entities_with_labels: List[EntityWithLabel]
    query: Optional[str]


class EntityDescription(BaseModel):
    uri: EntityURI
    label: Optional[List[LabelWithLang]]
    class_id: ClassURI
    longname: Optional[str]
    data_properties: List[PredicateLiteralTuple]
    object_properties: List[PredicateObjectTuple]
    inverse_properties: List[PredicateObjectTuple]


class EntityNeighbourhoodDescription(BaseModel):
    link_type: RelationURI
    entity: EntityURI
    entity_class: ClassURI
    labels: List[LabelWithLang]
    central_entity_role: RoleURI
    provenance: AbbreviatedProvenance
    relation_properties: AbbreviatedProvenance
    reification_uri: ReificationURI




