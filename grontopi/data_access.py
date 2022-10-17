import json
from abc import ABC, abstractmethod
from typing import List

from SPARQLWrapper import SPARQLWrapper, JSON
from pydantic import parse_obj_as

from models.api_models import EntityDescription, \
    EntityListWithLabels, EntityNeighbourhoodDescription
from models.entity_models import EntityWithLabel, LabelWithLang
from models.ontology_models import EntityURI, ClassURI, WrappedUri
from config import conf as cfg
from utils.rdfutils import URI, LIT


class GraphAccess(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def fetch_entities_from_list_of_ids(self, entitylist: List[EntityURI]) \
            -> List[EntityDescription]:
        pass

    @abstractmethod
    def fetch_entities_of_classes(self, class_id: ClassURI,
                                  start: int = 0,
                                  per_page: int = 1000,
                                  lang: str = "en") \
            -> EntityListWithLabels:
        pass

    @abstractmethod
    def check_existence_of_entities(self,
                                    entities: List[EntityURI]) \
            -> List[EntityURI]:
        pass

    @abstractmethod
    def fetch_entities_around(self, entity_id: EntityURI) \
            -> EntityNeighbourhoodDescription:
        pass


class SPARQLAccess(GraphAccess):
    def __init__(self, query_endpoint,
                 query_credentials=None):
        self.query_endpoint = query_endpoint
        self.query_client = SPARQLWrapper(self.query_endpoint)
        self.query_client.setReturnFormat(JSON)
        self.query_client.setMethod("POST")
        if query_credentials is not None:
            self.query_client.setCredentials(query_credentials[0],
                                             query_credentials[1])
        super().__init__()

    def fetch_entities_from_list_of_ids(self,
                                        entitylist: List[EntityURI]
                                        ) -> List[EntityDescription]:
        pass

    def fetch_entities_of_classes(self,
                                  class_id: ClassURI,
                                  start: int = 0,
                                  per_page: int = 1000,
                                  lang: str = "en"
                                  ) -> EntityListWithLabels:
        query = self._query_for_class(class_id, start, per_page, lang)
        self.query_client.setQuery(query)
        rj = self.query_client.queryAndConvert()

        # First we group labels by entities
        ent2labels = {}
        for binding in rj["results"]["bindings"]:
            entity = URI(binding["s"]["value"]).n3()
            current_labels = ent2labels.get(entity, [])
            labwithlang = {"label_predicate":
                str(URI(binding["label_pred"][
                            "value"]).n3()).replace('"',''),
                "label_value":
                    LIT(binding["label_val"]["value"]).n3(),
                "label_lang": lang
            }
            current_labels.append(LabelWithLang.parse_obj(labwithlang))
            ent2labels[entity] = current_labels

        # Now we present them as required by the output model
        entities_with_labels = []
        for entity, labels in ent2labels.items():
            ewl = {
                "entity": entity,
                "labels": labels,
                "longname": self._compute_long_name(labels),
                "class_id": class_id
            }
            entities_with_labels.append(EntityWithLabel.parse_obj(ewl))
        result = {"entities_with_labels": entities_with_labels}
        print(json.dumps(rj, indent=2))
        return EntityListWithLabels.parse_obj(result)

    def check_existence_of_entities(self,
                                    entities: List[EntityURI]
                                    ) -> List[EntityURI]:
        pass

    def fetch_entities_around(self,
                              entity_id: EntityURI
                              ) -> EntityNeighbourhoodDescription:
        pass

    # ToDo actually compute longname
    def _compute_long_name(self, labels: List[EntityWithLabel]):
        return "longname"

    @staticmethod
    def _query_for_class(class_id: ClassURI,
                         start: int = 0,
                         per_page: int = 1000,
                         lang: str = "en"
                         ):
        uniontermns = []
        for luri in cfg.label_uris:
            uterm = f"""
                        {{
                           ?s {URI(luri).n3()} ?label_val .
                           BIND ({URI(luri).n3()} AS ?label_pred) .
                        }}
                    """
            uniontermns.append(uterm)

        query = f"""
                SELECT ?s ?label_pred ?label_val
                WHERE {{
                    GRAPH ?g {{
                        ?s a {class_id} .
                    {"UNION".join(uniontermns)}
                    }} 
                    FILTER(LANG(?label_val) = '' 
                    || LANGMATCHES(LANG( ?label_val), '{lang}'))
                }}
                
                OFFSET {start} LIMIT {per_page}
                """
        return query
