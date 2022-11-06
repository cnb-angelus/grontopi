import math
import os
from typing import Dict, Union, List

import rdflib
from rdflib.paths import OneOrMore
from pydantic import parse_obj_as

from config import conf as cfg
from config import GrOntoPIConfig
from models.ontology_models import ClassDescription, ClassURI
from utils.rdfutils import URI, get_local_name


ontons = rdflib.namespace.Namespace(cfg.ontonamespace)
owl_ns = rdflib.namespace.OWL
rdf_ns = rdflib.namespace.RDF
a = rdf_ns["type"]
rdfs_ns = rdflib.namespace.RDFS
skos_ns = rdflib.namespace.SKOS

unionof_pred_str = "http://www.w3.org/2002/07/owl#unionOf"

vocab_class = ontons["Catalogo"]


def _union2list(r1):
    for k, v in r1.items():
        for subk in [get_local_name(rdfs_ns["domain"]),
                     get_local_name(rdfs_ns["range"])]:
            # l1 = len(v[subk])
            singlec = [x for x in v[subk] if type(x) is str]
            dictcl = [x for x in v[subk] if type(x) is dict
                      and "<http://www.w3.org/2002/07/owl#unionOf>"
                      in x.keys()]

            for di in dictcl:
                singlec += di["<http://www.w3.org/2002/07/owl#unionOf>"]

            r1[k][subk] = list(set(singlec))
    return r1


class OntologyReader:

    def __init__(self, ontologypath: str):
        # print("\nOntology Reader init: -------")

        # Ontology Specific
        self.reified_object_property = cfg.reified_object_property
        self.reified_data_property = cfg.reified_data_property
        self.materialized_property_types = cfg.materialized_property_types
        self.rangeOf = cfg.rangeOf
        self.domainOf = cfg.domainOf
        self.study_domain_class = cfg.study_domain_class
        self.reality_class = cfg.reality_class
        self.base_classes = cfg.base_classes
        self.sameness_predicate = cfg.sameness_predicate
        self.label_uris = cfg.label_uris

        self.superclasses = dict()

        self.graph = rdflib.Graph()
        self.graph.parse(ontologypath, format="ttl")

        # print("\t", len(self.graph), "triples in raw ontology")

        # print("\t Staring materialization of ontology")
        self.materialize_subclass_properties()
        self.materialize_domain_of_range_of()
        self.add_rdfs_labels()
        print("\t", len(self.graph), "triples in full ontology")

        self.rdfs_ns = rdflib.namespace.RDFS
        self.rdf_ns = rdflib.namespace.RDF
        # print("\n-------- :Ontology Reader init finished\n\n")

        # These are shortcuts to not re-compute the whole ontology often
        self.allrelations = self.get_relations().keys()
        self.allproperties = self.get_properties().keys()
        self.all_study_domain_classes = self.get_study_domain_classes().keys()
        self.class_hierarchy = dict()
        self.shoulders = dict()
        self._populate_shoulders()

    def add_rdfs_labels(self):
        self.graph.add((rdf_ns["type"], rdfs_ns["label"],
                        rdflib.Literal("belongs to class")))
        self.graph.add((rdf_ns["subject"], rdfs_ns["label"],
                        rdflib.Literal("has subject")))
        self.graph.add((rdf_ns["predicate"], rdfs_ns["label"],
                        rdflib.Literal("has predicate")))
        self.graph.add(
            (rdf_ns["object"], rdfs_ns["label"], rdflib.Literal("has object")))
        self.graph.add((rdfs_ns["subClassOf"], rdfs_ns["label"],
                        rdflib.Literal("is subclass of")))

    def materialize_subclass_properties(self):
        self.materialize_domain_of_range_of()
        class_dict = self.get_classes()
        for cluristr, cldata in class_dict.items():
            subcuris = set(cldata.subclasses)
            domof = [rdflib.URIRef(x[1:-1]) for x in cldata.isDomainOf]
            ranof = [rdflib.URIRef(x[1:-1]) for x in cldata.isRangeOf]
            to_check = set(subcuris)
            already_checked = set()
            while len(to_check) > 0:
                suburi_str = to_check.pop()

                d_ = self.superclasses.get(suburi_str, set())
                d_.add(cluristr)
                self.superclasses[suburi_str] = d_
                if suburi_str in already_checked:
                    continue
                already_checked.add(suburi_str)
                suburi = rdflib.URIRef(suburi_str[1:-1])
                for duri in domof:
                    # print(suburi.n3(), self.domainOf.n3(), duri.n3())
                    self.graph.add((suburi, self.domainOf, duri))
                for ruri in ranof:
                    # print(suburi.n3(), self.rangeOf.n3(), ruri.n3())
                    self.graph.add((suburi, self.rangeOf, ruri))
                thissubc = set(class_dict[suburi_str].subclasses)
                to_check = to_check | thissubc

    def materialize_domain_of_range_of(self):
        # Adds, to every class, a set of isDomainOf and isRangeOf triples
        # so that DESCRIBEing the class gives you information on what relations
        # and properties can be connected to it
        # In doing so expands unions in domain. If
        #     x rdfs:domain union_of a,b
        # Then:
        #     x rdfs:domain a
        #     x rdfs:domain b
        relation_dict = self.get_relations()
        property_dict = self.get_properties()
        for uri, rel in list(relation_dict.items()) + list(
                property_dict.items()):
            uri = rdflib.URIRef(uri[1:-1])
            dom_1 = rel["domain"]
            # print(type(dom))

            dom = []
            for d in dom_1:
                # print(d)
                if type(d) is dict:
                    d = d["<" + unionof_pred_str + ">"]
                if type(d) is list:
                    dom += d
                else:
                    dom.append(d)

            ran = rel["range"]
            # print("\n-----",dom,ran,"\n")
            # print("..\n..\n..")
            dom = [rdflib.URIRef(x[1:-1]) for x in dom]
            ran = [rdflib.URIRef(x[1:-1]) for x in ran]
            for relation_dict in dom:
                self.graph.add((relation_dict, self.domainOf, uri))
            for relation_dict in ran:
                self.graph.add((relation_dict, self.rangeOf, uri))

    def get_properties(self):
        r1 = self.get_relations(class_uri=rdf_ns["Property"])
        r2 = self.get_relations(owl_ns["ObjectProperty"])
        r1.update(r2)

        for dom, _, prop in self.graph.triples((None, self.domainOf, None)):
            if prop.n3() in r1.keys():
                thisprop = r1[prop.n3()]
                thisprop[get_local_name(rdfs_ns["domain"])].append(dom.n3())
                r1[prop.n3()] = thisprop

        for ran, _, prop in self.graph.triples((None, self.rangeOf, None)):
            if prop.n3() in r1.keys():
                thisprop = r1[prop.n3()]
                thisprop[get_local_name(rdfs_ns["range"])].append(ran.n3())
                r1[prop.n3()] = thisprop

        r1 = _union2list(r1)
        for prop, propdata in r1.items():

            ran0 = str(propdata[get_local_name(rdfs_ns["range"])][0])
            if ran0.startswith("<http://www.w3.org/2001/XMLSchema#"):
                r1[prop]["rangetype"] = "literal"
                if ran0 == "<http://www.w3.org/2001/XMLSchema#dateTime":
                    r1[prop]["rangetype"] = "datetime"
                continue
            t = [x for x in self.graph.triples(
                (rdflib.URIRef(ran0[1:-1]), a, vocab_class))]

            if len(t) > 0:
                r1[prop]["rangetype"] = "catalogue"
                continue
            r1[prop]["rangetype"] = "object"

        return r1

    def get_relations(self, class_uri=owl_ns["ObjectProperty"],
                      broader_uri=None):

        label_uris = {"label": rdfs_ns["label"]}
        sub_relation_title = None if broader_uri is None else "items"

        result = self.get_elements_with_hierarchies(
            s=None,
            class_uri=class_uri,
            broader_uri=broader_uri,
            label_uris=label_uris,
            sub_relation_title=sub_relation_title,
            subj_pred_uris=[
                rdfs_ns["domain"],
                rdfs_ns["range"]])
        if result is None:
            return result

        r1 = result["items"]

        return _union2list(r1)

    def get_catalogues(self, root_uri=None):
        class_uri = skos_ns["Concept"]
        broader_uri = skos_ns["broader"]
        label_uris = {"prefLabel": skos_ns["prefLabel"],
                      "altLabel": skos_ns["altLabel"]}
        sub_relation_title = "narrower"

        result = dict()
        if root_uri is not None:
            root_uri = URI(root_uri)

        for s, p, o in self.graph.triples((root_uri, a, vocab_class)):
            # print("catalog uri: ",s)
            rs = self.get_elements_with_hierarchies(
                s=s,
                class_uri=class_uri,
                broader_uri=broader_uri,
                label_uris=label_uris,
                sub_relation_title=sub_relation_title,
                maxlev=2)
            if rs is not None:
                result[s.n3()] = rs
        return result

    def get_study_domain_classes(self):
        all_classes = self.get_classes()
        res = dict()
        inspected = set()
        sdcls = parse_obj_as(ClassURI, self.study_domain_class.n3())
        to_inspect = set(
            all_classes[sdcls].subclasses + [sdcls])
        while len(to_inspect) > 0:
            cl = to_inspect.pop()
            if cl in inspected:
                continue
            inspected.add(cl)
            if cl not in self.base_classes:
                res[cl] = all_classes[cl]
            if len(all_classes[cl].subclasses) > 0:
                to_inspect = to_inspect | set(all_classes[cl].subclasses)

        return res

    def get_classes(self) -> Union[None, Dict[ClassURI, ClassDescription]]:
        """
        Get the classes of the ontology
        :return:  A dictionary whose keys are class URIs and whose values
            are dictionaries holding the info of each class.
            The info is a dictionary with keys 'label', 'subclasses',
            '...isDomainOf' and '...isRangeOf'.
        """
        broader_uri = rdfs_ns["subClassOf"]
        label_uris = {"label": rdfs_ns["label"]}
        sub_relation_title = "subclasses"

        result = self.get_elements_with_hierarchies(
            s=None,
            class_uri=owl_ns["Class"],
            broader_uri=broader_uri,
            label_uris=label_uris,
            sub_relation_title=sub_relation_title,
            subj_pred_uris=[
                self.domainOf,
                self.rangeOf]
        )
        if result is None:
            return result
        return {x: ClassDescription.parse_obj(v)
                for x, v in result["items"].items()}

    def expand(self, somenode):
        if type(somenode) is not rdflib.BNode:
            try:
                return somenode.n3()
            except Exception:
                # print("\n!!!!!!!!!!!----\n\n", somenode, type(somenode))
                return somenode.n3()
        for _, uni, p in self.graph.triples((somenode, None, None)):
            if uni == rdflib.URIRef(unionof_pred_str):
                lis = []
                tovisit = [p]
                while len(tovisit) > 0:
                    v = tovisit.pop()
                    for _, x, y in self.graph.triples((v, None, None)):
                        if x == rdf_ns["first"]:
                            lis.append(y)
                        if x == rdf_ns["rest"]:
                            tovisit.append(y)
                return {uni.n3(): [x.n3() for x in lis]}

        return "BLANK"

    def find_def_label_type(self, labeldict: dict):
        deflabtype = None
        for v in self.label_uris:
            if v in labeldict.values():
                return [k for k, v1 in labeldict.items()
                        if v1 == v][0]

        dictkeys = labeldict.keys()
        poslabs = [dk for dk in dictkeys if "label" in dk.lower()]
        if len(poslabs) > 0:
            deflabtype = poslabs[0]
        if len(dictkeys) > 1:
            labelordering = ["prefLabel", "label", "altLabel"]
            for ltype in labelordering:
                if ltype in dictkeys:
                    deflabtype = ltype
                    break
        return deflabtype

    @staticmethod
    def clean_n3_label(n3label: str):
        deflab = n3label
        if len(deflab) > 3:
            if deflab[-3] == "@" and deflab[-2:].isalpha():
                deflab = deflab[:-3]
            if deflab[0] == '"':
                deflab = deflab[1:]
            if deflab[-1] == '"':
                deflab = deflab[:-1]
        return deflab

    def get_elements_with_hierarchies(self, s=None,
                                      class_uri=owl_ns["Class"],
                                      broader_uri=rdfs_ns["subClassOf"],
                                      label_uris: dict = None,
                                      sub_relation_title="items",
                                      subj_pred_uris=None,
                                      maxlev=math.inf):
        """
        Returns info on all things of a certain class.
        If specified with broader_uri, a hierarchy of thing using this uri is
        returned

        Doesn't return things that don't have labels, to ignore blank nodes
        :param s: The top of the tree we are interested in (is not returned).
        If None (default) then all things of this class are returned
        :param class_uri: Determines the class of things we want
        :param broader_uri:  THe relation that defines what are children
        :param label_uris:  a "name":URI dictionary to get the labels of things
            e.g. {'prefLabel':skos:prefLabel}
        :param sub_relation_title:  how are children called? narrower?
        :param subj_pred_uris: a list of uris that return object properties of
             each thing
        :param maxlev how many leves to go through
        :return:
        """
        if subj_pred_uris is None:
            subj_pred_uris = []
        this_tree = dict()
        if label_uris is None:
            label_uris = {"label": rdfs_ns["label"]}

        deflabtype = self.find_def_label_type(label_uris)

        this_class = [c for c, _, _ in
                      self.graph.triples((None, a, class_uri))]
        if s is None:
            nodes_to_check = [c for c in this_class]
        else:
            nodes_to_check = [c for c, _, _ in
                              self.graph.triples((None, broader_uri, s))]

        if class_uri != skos_ns["Concept"]:
            exclude = [c for c, _, _ in
                       self.graph.triples((None, a, skos_ns["Concept"]))]
        else:
            exclude = []

        added = math.inf
        levels = {x: 0 for x in nodes_to_check}
        while added > 0:
            added = 0
            while len(nodes_to_check) > 0:
                this_node = nodes_to_check.pop()
                if this_node not in this_class or this_node in exclude:
                    continue

                # We find, if needed, the children
                if broader_uri is None:
                    item_desc = this_tree.get(this_node,
                                              {labtype: [] for labtype in
                                               label_uris})
                else:
                    item_desc = this_tree.get(this_node,
                                              dict({labtype: [] for labtype in
                                                    label_uris},
                                                   **{sub_relation_title: []}))
                    children = []
                    if levels[this_node] <= maxlev:
                        children = [c.n3() for c, _, _
                                    in self.graph.triples((None,
                                                           broader_uri,
                                                           this_node))]
                        levels.update(
                            {child: levels[this_node] + 1 for child in
                             children})
                    if len(children) > 0:
                        nodes_to_check = list(
                            set(nodes_to_check + children) - this_tree.keys())
                    item_desc[sub_relation_title] += children

                # We find the labels of this node
                numlabs = 0
                for labtype, laburi in label_uris.items():
                    item_desc[labtype] += [c.n3() for _, _, c
                                           in self.graph.triples((this_node,
                                                                  laburi,
                                                                  None))]
                    numlabs += len(item_desc[labtype])

                # We only add nodes which have at least one label,
                #    to avoid blank nodes
                if numlabs <= 0:
                    continue

                # Here we assign a default label
                deflab = ""
                deflabtype_ = deflabtype
                if deflabtype not in item_desc.keys():
                    deflabtype_ = self.find_def_label_type(item_desc)
                if deflabtype_ is not None:
                    deflab = item_desc[deflabtype_][0]
                    deflab = self.clean_n3_label(deflab)

                item_desc["default_label"] = deflab

                for pr in subj_pred_uris:
                    ll = [self.expand(ob) for _, _, ob in
                          self.graph.triples((this_node, pr, None)) if
                          (type(ob) is rdflib.URIRef
                           or
                           type(ob) is rdflib.BNode)]
                    item_desc[get_local_name(pr)] = ll

                this_tree[this_node.n3()] = item_desc
                added += 1

        this_tree_names = [[c.n3() for _, _, c
                            in self.graph.triples((s, laburi, None))]
                           for laburi in label_uris.values()]
        this_tree_names = [item for sublist in this_tree_names for item in
                           sublist]

        if len(this_tree_names) > 0:
            return {"labels": this_tree_names,
                    "items": this_tree,
                    "default_label": self.clean_n3_label(this_tree_names[0])}
        return None

    def _discover_shoulder(self, class_uri_str):
        if "<" == class_uri_str[0]:
            class_uri_str = class_uri_str[1:-1]
        class_uri = URI(class_uri_str)
        if class_uri in self.shoulders.keys():
            return self.shoulders[class_uri]

        splitter = "#" if "#" in class_uri_str else "/"
        class_local_name = str(class_uri_str.split(splitter)[-1])
        plural_suffix: str = "es"
        if class_local_name[-1] in ["a", "e", "i", "o", "u"]:
            plural_suffix = "s"

        return class_local_name.lower() + plural_suffix

    def _populate_shoulders(self):
        for bc_ in self.base_classes:
            bc = URI(bc_)
            self.class_hierarchy[bc.n3()] = 0
            for sc, _, _ in self.graph.triples(
                    (None, rdfs_ns["subClassOf"], bc)):
                self.class_hierarchy[sc.n3()] = 1
                shoulder = self._discover_shoulder(sc.n3())
                for ssc, _, _ in self.graph.triples(
                        (None, rdfs_ns["subClassOf"] * OneOrMore, sc)):
                    self.class_hierarchy[ssc.n3()] = 2
                    k = ssc.n3()[1:-1]
                    self.shoulders[k] = shoulder

    def get_maximal_class(self, classlist: List[ClassURI]):
        """
        For a given set of classes, returns the narrowest of them.
        It is useful, e.g., to present to the user the most specific class
        isntead of something very general like Things
        :param classlist:
        :return:
        """
        classlevels = {cl: self.class_hierarchy[cl]
                       for cl in classlist if
                       cl in self.class_hierarchy.keys()}
        if len(classlevels) == 0:
            # print("-->\nno levels found for ",classlist,"\n<--!")
            return URI(self.study_domain_class).n3()

        maxl = max(list(classlevels.values()))
        maxi = [x for x, v in classlevels.items() if v == maxl][0]

        return maxi
