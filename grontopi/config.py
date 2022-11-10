import json
import logging
import os.path
from os import environ
from typing import List, Union

import rdflib

owl_ns = rdflib.namespace.OWL
rdf_ns = rdflib.namespace.RDF
a = rdf_ns["type"]
rdfs_ns = rdflib.namespace.RDFS
skos_ns = rdflib.namespace.SKOS

overrideable_sections = ["ontology_config", "oauth2_config"]


class GrOntoPIConfig:
    def __init__(self):
        # The default configuration. If no config file is loaded
        self.use_OAuth2 = False
        self.auth_server_kid = None
        self.auth_server_n = None
        self.interservices_token = None
        self.ontonamespace = "http://www.wikidata.org/wiki/"
        self.sparql_endpoint = "https://query.wikidata.org/bigdata/namespace/wdq/sparql"
        self.sparql_credentials = None
        self.ontology_path = "/config/ontology.owl"
        self.type_predicate = ["http://www.wikidata.org/prop/direct/P31",
                               # instance of
                               "http://www.wikidata.org/prop/direct/P106"
                               # has profession
                               ]
        self.different_graphs = False


        # OpenAPI examples
        self.openAPIExamples = {
            "entities": ["http://www.wikidata.org/entity/Q7243",  # Tolstoi
                         "http://www.wikidata.org/entity/Q161531", # War&Peace
                         ],
            "classes": ["http://www.wikidata.org/entity/Q36180"],  # Writer
            "default_language": "en"
        }

        # Ontology configuration
        ontons = rdflib.namespace.Namespace(self.ontonamespace)
        self.reified_object_property = ontons["MaterializedObjectProperty"]
        self.reified_data_property = ontons["MaterializedDataProperty"]
        self.materialized_property_types = ontons["PropertyType"]
        self.rangeOf = ontons["isRangeOf"]
        self.domainOf = ontons["isDomainOf"]
        # ---------- Base classes
        self.study_domain_class = ontons["ThingsDomain"]
        self.reality_class = ontons["ThingsReality"]
        self.base_classes = [self.study_domain_class, self.reality_class]
        self.sameness_predicate = owl_ns["sameAs"]
        self.label_uris = [rdfs_ns["label"],
                           skos_ns["prefLabel"],
                           ]

        self.redis_cache_url = "redis_cache"
        self.redis_cache_port = "6379"

    def load_json_config(self, config_path):
        if os.path.isfile(config_path):
            with open(config_path) as fin:
                cj = json.loads(fin.read())
                if "ontonamespace" in cj.keys():
                    self.ontonamespace = cj["ontonamespace"]
                    self._reset_defaults_with_new_ns()
                for section in overrideable_sections:
                    if section in cj.keys():
                        for k, v in cj[section].items():
                            if isinstance(v, list):
                                vuri = [self._uri(ite, section)
                                        for ite in v]
                            else:
                                vuri = self._uri(v, section)
                            self.__dict__[k] = vuri
                        cj.pop(section)
                self.__dict__.update(cj)
            self.base_classes = [self.study_domain_class, self.reality_class]
        else:
            logging.warning("Loading default configuration")

    def _uri(self, v: str, sectionname: str):
        if not sectionname == "ontology_config":
            return v
        if "://" in v:
            return rdflib.URIRef(v)
        else:
            ontons = rdflib.namespace.Namespace(self.ontonamespace)
            return ontons[v]

    def _reset_defaults_with_new_ns(self):
        ontons = rdflib.namespace.Namespace(self.ontonamespace)
        self.reified_object_property = ontons["MaterializedObjectProperty"]
        self.reified_data_property = ontons["MaterializedDataProperty"]
        self.materialized_property_types = ontons["PropertyType"]
        self.rangeOf = ontons["isRangeOf"]
        self.domainOf = ontons["isDomainOf"]
        self.study_domain_class = ontons["ThingsDomain"]
        self.reality_class = ontons["ThingsReality"]
        self.base_classes = [self.study_domain_class, self.reality_class]


conf = GrOntoPIConfig()

# The default location of a config file
configpath = "/config/config.json"
# The config file location can be overriden with an env variable
if environ.get("CONFIG_PATH") is not None:
    configpath = os.environ.get("CONFIG_PATH")
    if not os.path.isfile(configpath):
        logging.error("config file provided, but it can't be found")
        raise FileNotFoundError

# If the config file exists, we use it to overide configs
conf.load_json_config(configpath)
print(conf.__dict__.items())