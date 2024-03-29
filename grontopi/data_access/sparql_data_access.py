import json
import asyncio
from typing import List, Dict, Set, Tuple

import rdflib
import unidecode
from SPARQLWrapper import SPARQLWrapper, JSON
from pydantic import parse_obj_as
from aiocache import Cache

from models.api_models import EntityDescription, \
    EntityListWithLabels, EntityNeighbourhoodSummary

from models.entity_models import EntityWithLabel, LabelWithLang
from models.ontology_models import EntityURI, ClassURI
from models.ontology_models import RelationURI, RoleURI
from models.entity_models import PredicateObjectTuple
from config import conf as cfg
from utils.rdfutils import URI, LIT
from utils.owlreading import OntologyReader
from data_access.abstract_data_access import GraphAccess

cache = Cache(cache_class=Cache.REDIS,
              namespace="main",
              endpoint=cfg.redis_cache_url,
              port=int(cfg.redis_cache_port))

print("Trying redis at",
      cfg.redis_cache_url,
      cfg.redis_cache_port, "\n\n")


class SPARQLAccess(GraphAccess):
    def __init__(self, query_endpoint,
                 query_credentials=None,
                 typepred=rdflib.namespace.RDF["type"],
                 different_graphs=False):
        self.query_endpoint = query_endpoint
        user_agent = 'Grontogopi/0.1 (' \
                     'https://github.com/cnb-angelus/grontopi; ' \
                     'grontopi@gmail.com)'

        print(self.query_endpoint, "\t<~~~~~~~ Endpoint")
        self.query_client = SPARQLWrapper(self.query_endpoint,
                                          agent=user_agent)
        self.query_client.setReturnFormat(JSON)
        self.query_client.setMethod("POST")
        if query_credentials is not None and len(query_credentials) == 2:
            self.query_client.setCredentials(query_credentials[0],
                                             query_credentials[1])

        self.typepred_list = [rdflib.namespace.RDF["type"]]
        if isinstance(typepred, rdflib.URIRef) or isinstance(typepred, str):
            self.typepred_list = [URI(typepred)]
        if isinstance(typepred, list):
            self.typepred_list = [URI(x) for x in typepred]

        self.differentgraphs = different_graphs
        self._varname2labelpred = {"?labvar_" + str(i): lu
                                   for i, lu in enumerate(cfg.label_uris)}
        super().__init__()

    async def _query(self, query, no_cache=False):
        """
        This method just takes care of the SPARQL query, choosing the right
        HTTP verb as per WikiData recommendation to use GET for small queries
        :param query:
        :return:
        """
        query_clean = "\n".join([x.strip() for x in query.split("\n")])
        cached_value = await cache.get(query_clean, default=None)
        if cached_value is not None:
            print("Cache hit")
            return cached_value
        self.query_client.setQuery(query_clean)
        self.query_client.setMethod("GET")
        if no_cache or len(query_clean) > 1000:
            self.query_client.setMethod("POST")
        resp = self.query_client.queryAndConvert()
        await cache.set(query_clean, resp)
        print("Cache miss")
        return resp

    async def fetch_entities_from_list_of_ids(self,
                                              entitylist: List[EntityURI],
                                              onto: OntologyReader,
                                              lang: str = "en",
                                              force_full=False,
                                              ) -> List[EntityDescription]:
        print(self.query_endpoint, "<--- Different graphs\n\n")
        classgetter = self._get_classes_for_entities(
            entitylist=entitylist,
            onto_config=onto)

        labgetter = self._get_labels_for_entities(entitylist=entitylist,
                                                  lang=lang)

        ent2class, ent2labels = await asyncio.gather(classgetter, labgetter)

        entity_descriptions = []
        allmissinglabels = set()
        for entity, labels in ent2labels.items():
            ewl = {
                "uri": entity,
                "label": labels,
                "longname": self._compute_long_name(labels=labels),
                "class_id": ent2class[entity],
                "data_properties": [],
                "object_properties": [],
                "inverse_properties": [],
            }
            if force_full or len(entitylist) == 1:
                ewl, _missinglabs = await self._add_links_to_entity(ewl=ewl,
                                                                    onto=onto,
                                                                    lang=lang)
                _missinglabs: Set[EntityURI]
                allmissinglabels.update(_missinglabs)

            entity_descriptions.append(EntityDescription.parse_obj(ewl))

        newlabels = await self._get_labels_for_entities([x
                                                         for x
                                                         in allmissinglabels],
                                                        lang=lang)

        for ed in entity_descriptions:
            ed: EntityDescription
            for op in ed.object_properties + ed.inverse_properties:
                op: PredicateObjectTuple
                euri = URI(op.object).n3()
                nl = newlabels.get(euri, [])
                op.object_labels = nl
        return entity_descriptions

    async def fetch_entities_of_classes(self,
                                        class_id: ClassURI,
                                        start: int = 0,
                                        per_page: int = 1000,
                                        lang: str = "en",
                                        prefix: str = "",
                                        ) -> EntityListWithLabels:
        query = self._query_entities_of_class(class_id, start,
                                              per_page,
                                              lang, prefix)

        rj = await self._query(query)
        ent2labels = self._collect_labels_for_entities(rj)

        # Now we present them as required by the output model
        entities_with_labels = []
        for entity, labels in ent2labels.items():
            ewl = {
                "entity": entity,
                "labels": labels,
                "longname": self._compute_long_name(labels=labels),
                "class_id": class_id
            }
            entities_with_labels.append(EntityWithLabel.parse_obj(ewl))
        result = {"entities_with_labels": entities_with_labels}
        return EntityListWithLabels.parse_obj(result)

    async def check_existence_of_entities(self,
                                          entities: List[EntityURI],
                                          onto_config: OntologyReader
                                          ) -> List[EntityURI]:

        classes = await self._get_classes_for_entities(
            entitylist=entities,
            onto_config=onto_config)
        found = set([x for x in classes.keys()])
        origentities = set([URI(e).n3() for e in entities])
        return [parse_obj_as(EntityURI, e)
                for e in origentities.difference(found)]

    async def fetch_entities_around(self,
                                    entity_id: EntityURI,
                                    onto_config: OntologyReader,
                                    lang: str = "en",
                                    ) -> EntityNeighbourhoodSummary:
        ewl = {"uri": URI(entity_id).n3()}
        ewl, ents = await self._add_links_to_entity(ewl, onto=onto_config,
                                                    lang=lang)
        ents = [parse_obj_as(EntityURI, x) for x in ents]
        descs = await self.fetch_entities_from_list_of_ids(entitylist=ents,
                                                           lang=lang,
                                                           onto=onto_config,
                                                           force_full=False)
        descsdict = {URI(de.uri).n3(): de for de in descs}
        linkedents = []
        linkcount = dict()
        subron3 = parse_obj_as(RoleURI, onto_config.rdf_ns["subject"].n3())
        preron3 = parse_obj_as(RoleURI, onto_config.rdf_ns["predicate"].n3())
        for op, rol in [(x, subron3) for x in ewl["object_properties"]] + \
                       [(x, preron3) for x in ewl["inverse_properties"]]:
            op: PredicateObjectTuple
            entn3 = URI(op.object).n3()
            entdeesc = descsdict[entn3]
            entdeesc: EntityDescription
            pn3 = URI(op.predicate).n3()
            cn3 = URI(entdeesc.class_id).n3()
            neighbor_desct = {"link_type": op.predicate,
                              "entity": op.object,
                              "entity_class": entdeesc.class_id,
                              "labels": entdeesc.label,
                              "central_entity_role": rol
                              }
            linkedents.append(neighbor_desct)
            thisclass = linkcount.get(cn3, dict())
            thisclass[pn3] = 1 + thisclass.get(pn3, 0)
            linkcount[cn3] = thisclass

        result = {"linked_entities": linkedents, "link_count": linkcount}
        return parse_obj_as(EntityNeighbourhoodSummary, result)

    # ToDo make this work for a list of entities, to make a single query
    async def _add_links_to_entity(self,
                                   ewl: Dict,
                                   onto: OntologyReader,
                                   lang: str) -> Tuple[Dict, Set]:
        eid = ewl["uri"]
        query_links = self._query_entity_links(entity_id=eid,
                                               onto_cfg=onto)
        rjlinks_ = await self._query(query_links)
        rjlinks = rjlinks_["results"]["bindings"]

        dps, ops, ips = [], [], []
        ents = set()

        for binding in rjlinks:
            sub = URI(binding["s"]["value"]).n3()
            pre = URI(binding["p"]["value"]).n3()
            oty = binding["o"]["type"]
            if oty == "uri":
                obj = URI(binding["o"]["value"]).n3()
            else:
                if binding["o"].get("xml:lang", lang) != lang:
                    continue
                obj = binding["o"]["value"].replace('"', '').strip()

            tup = {"predicate": parse_obj_as(RelationURI, pre)}
            if oty == "uri":
                if sub == eid:
                    tup["object"] = parse_obj_as(EntityURI, obj)
                    ops.append(parse_obj_as(PredicateObjectTuple, tup))
                    ents.add(obj)
                else:
                    tup["object"] = parse_obj_as(EntityURI, sub)
                    ips.append(parse_obj_as(PredicateObjectTuple, tup))
                    ents.add(sub)
            else:
                tup["literal"] = obj
                dps.append(tup)

        newdesc = {"data_properties": dps,
                   "object_properties": ops,
                   "inverse_properties": ips}
        ewl.update(newdesc)
        return ewl, ents

    async def _get_labels_for_entities(self, entitylist: List[EntityURI],
                                       lang: str = "en"):
        query_labels = self._query_many_entity_labels(entity_ids=entitylist,
                                                      lang=lang)
        # Here we get the set of labels for every entity
        rjlabs = await self._query(query_labels)
        ent2labels = self._collect_labels_for_entities(rjlabs)
        return ent2labels

    async def _get_classes_for_entities(self,
                                        entitylist: List[EntityURI],
                                        onto_config: OntologyReader):
        query_classes = self._query_many_entity_classes(entity_ids=entitylist,
                                                        onto_cfg=onto_config,
                                                        )
        rjcls = await self._query(query_classes)
        ent2classes = self._group_classes_by_entity(rjcls)
        ent2class = {ent: onto_config.get_maximal_class(classes)
                     for ent, classes in ent2classes.items()}
        return ent2class

    @staticmethod
    def _compute_long_name(labels: List[LabelWithLang]):
        longname = ""
        for lwl in labels:
            longname += lwl.label_value.lower() + " "
            longname += unidecode.unidecode(lwl.label_value.lower()) + " "
        return longname

    # ToDo get all labels in a single binding, using OPTIONAL
    def _query_many_entity_labels(self,
                                  entity_ids: List[EntityURI],
                                  lang: str = "en"):
        graphextra_start = "GRAPH ?g {" if self.differentgraphs else "\n"
        graphextra_end = "}" if self.differentgraphs else "\n"

        label_optionals = ""
        filterparts = []
        for vn, lp in self._varname2labelpred.items():
            label_optionals += f"OPTIONAL {{ ?s {URI(lp).n3()}  {vn}  }} . \n"
            filter = f"(!BOUND({vn}) || LANG({vn})='{lang}')\n"
            filterparts.append(filter)
        filters = "FILTER(\n " + " && ".join(filterparts) + "\n)"

        subjvalues = " ".join([URI(eid).n3() for eid in entity_ids])
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
                 SELECT ?s {" ".join([vn
                                      for vn in self._varname2labelpred.keys()
                                      ])}
                 WHERE {{
                     {graphextra_start}
                         VALUES ?s {{ {subjvalues} }}
                    {label_optionals}
                    {graphextra_end}
                    {filters}
                 }}

                 """
        return query

    def _query_entity_links(self,
                            entity_id: EntityURI,
                            onto_cfg: OntologyReader):

        graphextra_start = "GRAPH ?g {" if self.differentgraphs else "\n"
        graphextra_end = "}" if self.differentgraphs else "\n"

        allowed_classes = onto_cfg.all_study_domain_classes
        allowed_classes = ", ".join([URI(clsuri).n3() for clsuri in
                                     allowed_classes])
        predvalues = list(onto_cfg.allrelations) + list(onto_cfg.allproperties)
        predvalues = " ".join([URI(puri).n3() for puri in predvalues])

        typepreds = " ".join([URI(x).n3() for x in self.typepred_list])

        euri = URI(entity_id).n3()
        query = f"""
                 SELECT DISTINCT ?s ?p ?o
                 WHERE {{
                     {graphextra_start}
                         VALUES ?p {{ {predvalues} }}
                         VALUES ?typepred {{ {typepreds}  }}
                         {{ 
                            {euri} ?p ?o .
                            BIND ({euri} AS ?s) . 
                            OPTIONAL {{ ?o ?typepred ?cls }}
                          }}
                         UNION
                         {{
                            ?s ?p {euri} .
                            ?s  ?typepred ?cls
                            BIND ({euri} AS ?o)
                         }}
                        {graphextra_end}
                     FILTER( isLiteral(?o) || ?cls in ( {allowed_classes} )  ) 
                 }}        
                 """
        return query

    def _query_many_entity_classes(self,
                                   entity_ids: List[EntityURI],
                                   onto_cfg: OntologyReader):

        graphextra_start = "GRAPH ?g {" if self.differentgraphs else "\n"
        graphextra_end = "}" if self.differentgraphs else "\n"

        allowed_classes = onto_cfg.all_study_domain_classes
        allowed_classes = ", ".join([URI(clsuri).n3() for clsuri in
                                     allowed_classes])
        subjvalues = " ".join([URI(eid).n3() for eid in entity_ids])
        typepreds = " ".join([URI(x).n3() for x in self.typepred_list])
        query = f"""
                 SELECT ?s ?cls
                 WHERE {{
                     {graphextra_start}
                         VALUES ?s {{ {subjvalues} }}                         
                         ?s ?typepred ?cls .
                         VALUES ?typepred {{ {typepreds}  }}
                     {graphextra_end}
                     FILTER(?cls in ( {allowed_classes} ) )
                 }}        
                 """
        return query

    def _query_entities_of_class(self,
                                 class_id: ClassURI,
                                 start: int = 0,
                                 per_page: int = 1000,
                                 lang: str = "en",
                                 prefix: str = "",
                                 ):
        """
        Creates a query with variables ?s ?label_pred ?label_val
        This query will return a binding for every entity,label pair
        :param class_id: The URI of the class of entities
        :param start:    The
        :param per_page:
        :param lang:
        :return:
        """
        label_optionals = ""

        filterparts = []
        for vn, lp in self._varname2labelpred.items():
            label_optionals += f"OPTIONAL {{ ?s {URI(lp).n3()}  {vn}  }} . \n"
            filter = f"(!BOUND({vn}) || LANG({vn})='{lang}')\n"
            filterparts.append(filter)

        if len(prefix) > 2:
            stringmatcher = f" (STRSTARTS(LCASE(?labvar_0)," \
                            f" '{prefix.lower()}'))  \n"
            filterparts.append(stringmatcher)
        filters = "FILTER(\n " + " && ".join(filterparts) + "\n)"

        graphextra_start = "GRAPH ?g {" if self.differentgraphs else "\n"
        graphextra_end = "}" if self.differentgraphs else "\n"

        typepreds = " ".join([URI(x).n3() for x in self.typepred_list])

        query = f"""
                SELECT ?s {" ".join([vn
                                     for vn in self._varname2labelpred.keys()
                                     ])}
                WHERE {{
                    {graphextra_start}
                    VALUES ?typepred {{ {typepreds}  }}
                        ?s  ?typepred {class_id} .
                    {label_optionals}
                    {graphextra_end}
                    {filters}
                }}

                OFFSET {start} LIMIT {per_page}
                """
        return query

    @staticmethod
    def _group_classes_by_entity(response_json: List[Dict]) -> Dict:
        ent2classes = {}
        for binding in response_json["results"]["bindings"]:
            entity = URI(binding["s"]["value"]).n3()
            current_classes = ent2classes.get(entity, [])
            theclass = URI(binding["cls"]["value"]).n3()
            current_classes.append(theclass)
            ent2classes[entity] = current_classes
        return ent2classes

    def _collect_labels_for_entities(self, response_json):
        ent2labels = {}
        for binding in response_json["results"]["bindings"]:
            entity = URI(binding["s"]["value"]).n3()
            current_labels = ent2labels.get(entity, [])
            for _varname, pred in self._varname2labelpred.items():
                varname = _varname[1:]
                if varname in binding.keys():
                    labpred = str(URI(pred).n3())
                    labval = LIT(binding[varname]["value"]).n3()
                    lablang = LIT(binding[varname]["xml:lang"]).n3()
                    labwithlang = {"label_predicate": labpred.replace('"', ''),
                                   "label_value": labval.replace('"', ''),
                                   "label_lang": lablang.replace('"', '')
                                   }
                    current_labels.append(LabelWithLang.parse_obj(labwithlang))
            ent2labels[entity] = current_labels

        return ent2labels
