from abc import ABC, abstractmethod
from typing import List, Dict, Set, Tuple

from models.api_models import EntityDescription, \
    EntityListWithLabels, EntityNeighbourDescription
from models.ontology_models import EntityURI, ClassURI

from utils.owlreading import OntologyReader


class GraphAccess(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def fetch_entities_from_list_of_ids(self,
                                        entitylist: List[EntityURI],
                                        onto_config: OntologyReader,
                                        lang) -> List[EntityDescription]:
        pass

    @abstractmethod
    def fetch_entities_of_classes(self, class_id: ClassURI,
                                  start: int = 0,
                                  per_page: int = 1000,
                                  prefix: str = "",
                                  lang: str = "en") -> EntityListWithLabels:
        pass

    @abstractmethod
    def check_existence_of_entities(self,
                                    entities: List[EntityURI],
                                    onto_config) -> List[EntityURI]:
        pass

    @abstractmethod
    def fetch_entities_around(self, entity_id: EntityURI,
                              onto_config: OntologyReader,
                              lang: str) -> EntityNeighbourDescription:
        pass
