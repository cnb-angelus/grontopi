from typing import List, Optional, Dict

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




class EntityNeighbourDescription(BaseModel):
    link_type: RelationURI
    entity: EntityURI
    entity_class: ClassURI
    labels: List[LabelWithLang]
    central_entity_role: RoleURI
    provenance: Optional[AbbreviatedProvenance]
    relation_properties: Optional[AbbreviatedProvenance]
    reification_uri: Optional[ReificationURI]

class EntityNeighbourhoodSummary(BaseModel):
    linked_entities : List[EntityNeighbourDescription]
    link_count : Dict[ClassURI,Dict[RelationURI, int]]