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


class GrOntoPIConfig:
    def __init__(self):
        # The default configuration. If no config file is loaded
        self.use_OAuth2 = False
        self.auth_server_kid = None
        self.auth_server_n = None
        self.default_useremail = None
        self.interservices_token = None
        self.owl_directory = None
        self.ontonamespace = "https://www.wikidata.org/wiki/"
        self.sparql_endpoint = "https://query.wikidata.org/sparql"
        self.sparql_credentials = None
        self.ontology_path = "/config/ontology.owl"

        # OpenAPI examples
        self.openAPIExamples = {
            "entities": ["https://www.wikidata.org/wiki/Q161531",
                         "https://www.wikidata.org/wiki/Q7243"],
            "classes" : ["https://www.wikidata.org/wiki/Q5"],
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

    def load_json_config(self, config_path):
        if os.path.isfile(config_path):
            with open(config_path) as fin:
                cj = json.loads(fin.read())
                if "ontonamespace" in cj.keys():
                    self.ontonamespace = cj["ontonamespace"]
                    self._reset_defaults_with_new_ns()
                if "ontology_config" in cj.keys():
                    for k, v in cj["ontology_config"].items():
                        if isinstance(v, list):
                            vuri = [self._uri(ite) for ite in v]
                        else:
                            vuri = self._uri(v)
                        self.__dict__[k] = vuri
                    cj.pop("ontology_config")
                self.__dict__.update(cj)

            self.base_classes = [self.study_domain_class, self.reality_class]
        else:
            logging.warning("Loading default configuration")

    def _uri(self, v: str):
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
