import json
from wikimapper import WikiMapper

import rdflib
import re
from uuid import uuid4
from typing import Dict, Tuple, List

fnwikipediainput = "sample_data/leaders_20221211.txt"
fnttl = "sample_data/leaders_20221211.ttl"
fnowl = "config/ontology_sample.owl"
fnconfig = "config/sample_config.json"
mappingfile = "index_enwiki-20190420.db"

rdftype = rdflib.RDF["type"]


def links_from_cell(colval: str,
                    exclude_lists: bool = True):
    linkpattern = re.compile('\[\[(.*?)\]\]')
    result = []
    for lt in re.findall(linkpattern, colval):
        if "|" in lt:
            lt = lt.split("|")[0]
        if exclude_lists and lt.lower().startswith("list of"):
            continue
        if lt.lower().startswith("file:"):
            continue
        result.append(lt.replace(" ", "_"))
    return result


def localname(uri: rdflib.URIRef):
    st = uri.n3()[1:-1]
    if "#" in st:
        return st.split("#")[-1]
    return st.split("/")[-1]


class WikimarkupDynamicList:
    def __init__(self, source, sep="  \t  "):
        self.text = source
        self.class_to_find = '"wikitable sortable"'
        self.columns = []
        self.content = []
        self.parse()
        self.sep = sep

    def collec_links(self,
                     link_ns: rdflib.namespace.Namespace,
                     cols=None,
                     exclude_lists: bool = True,
                     ):
        if cols is None:
            cols = self.columns
        result = []
        for cd in self.content:
            for cn in cols:
                colval: str = cd[cn]
                linkscell = links_from_cell(colval,
                                            exclude_lists=exclude_lists)
                result += [link_ns[lc]
                           for lc in linkscell]

        return set(result)

    def __str__(self):
        res = ""
        res += self.sep.join(self.columns) + "\n"
        for cd in self.content:
            res += "--------------------------------------------------------\n"
            res += self.sep.join([cd[cn]
                                  for cn in self.columns]) + "\n"
        res += "---------------------------------------------------------"
        return res

    def _process_sorname(self, snmarkup_: str):
        if snmarkup_.startswith("|{{"):
            snmarkup_ = snmarkup_[1:]
        snmarkup = snmarkup_.replace("{{", "").replace("}}", "")
        parts = snmarkup.split("|")
        numparts = len(parts)
        sortname = parts[0]
        first = parts[1]
        last = parts[2]
        if numparts > 3:
            link_target = parts[3]
        else:
            link_target = first + " " + last
        return "[[" + link_target + "]]"

    def _proces_flag(self, a: str):
        if "[[" in a and "]]" in a:
            res = a[a.index("}}") + 2:].strip()
            return res
        a = a.replace("{{", "").replace("}}", "")
        asp = a.split("|")
        if len(asp) == 3 and asp[2].lower().startswith("name="):
            res = "[[" + asp[2][5:] + "]]"
        else:
            res = "[[" + asp[1] + "]]"
        print("FLAG", a, res)
        if a.lower().startswith("dts|"):
            res = res.replace("[","").replace("]","")
        return res

    def _colvals2dict(self, colvalues):
        thisdict = dict()
        for cnu, cna in enumerate(self.columns):
            thisdict[cna] = colvalues[cna]
        return thisdict

    def parse(self):
        found_list = False
        colvalues = dict()
        colcounters = dict()
        currcol = 0
        for row in self.text.split("\n"):
            srow = row.strip()
            srow: str
            if not found_list:
                if (srow.startswith("{| class=")
                        and srow.endswith(self.class_to_find)):
                    found_list = True
                continue
            if srow == "|}":
                break
            if srow.startswith("!"):
                srow = srow.replace("!", "")
                colname = srow.split("|")[-1]
                self.columns.append(colname)
                colvalues[colname] = None
                colcounters[colname] = 0
            if srow.startswith("|-"):
                row_length = 0
                while currcol < len(self.columns):
                    colname = self.columns[currcol]
                    colval = colvalues[colname]
                    colcounters[colname] -= 1
                    colvalues[colname] = colval
                    currcol += 1
                self.content.append(self._colvals2dict(colvalues))
                currcol = 0
                print("-")
                continue
            colname = self.columns[currcol]
            print(" row: ", srow)
            while colcounters[colname] > 0:
                colname = self.columns[currcol]
                colval = colvalues[colname]
                colcounters[colname] -= 1
                colvalues[colname] = colval
                print(" Skipping ", currcol, colname, ":", colval, "count",
                      colcounters[colname] + 1)
                currcol += 1
                colname = self.columns[currcol]
            if currcol >= len(self.columns):
                row_length = 0
                self.content.append(self._colvals2dict(colvalues))
                currcol = 0
                continue
            else:
                colval = srow
                if "rowspan=" in srow:
                    colval = "|".join(srow.split("|")[2:])
                    a = srow.split("|")[1]
                    r = int(a.replace("rowspan=", '').replace('"', '').strip())
                    colcounters[colname] = r - 1
                if "sortname|" in colval:
                    colval = self._process_sorname(colval)
                if colval.startswith("|"):
                    colval = colval[1:].strip()
                if (colval.lower().startswith("{{flag")
                        or colval.lower().startswith("{{sfn")
                        or colval.lower().startswith("{{dts")):
                    colval = self._proces_flag(colval)
            colvalues[colname] = colval
            currcol += 1

        thisdict = dict()
        for cnu, cna in enumerate(self.columns):
            thisdict[cna] = colvalues[cna]
        self.content.append(thisdict)

        print("Parsing finished")


class Records2RDF:
    def __init__(self, record_class: rdflib.URIRef,
                 column_classes: Dict[str, rdflib.URIRef],
                 row_to_oolumn_links: Dict[str, rdflib.URIRef],
                 intercolumn_links: Dict[Tuple, rdflib.URIRef],
                 rowname_pattern: str,
                 entity_namespace: rdflib.namespace.Namespace,
                 labelpred: rdflib.URIRef = rdflib.RDFS["label"],
                 lang: str = "en"):
        self.record_class = record_class
        self.column_classes = column_classes
        self.row_to_oolumn_links = row_to_oolumn_links
        self.intercolumn_links = intercolumn_links
        self.rownamepattern = rowname_pattern
        self.entns = entity_namespace
        self.labelpred = labelpred
        self.lang = lang
        self.urimapper = WikiMapper(mappingfile)

    def _get_uri(self, localname):
        origurl = self.entns[localname].n3()[1:-1]
        wdid = self.urimapper.url_to_id(origurl)
        if wdid is None:
            return rdflib.URIRef(origurl)
        newuri = "http://www.wikidata.org/entity/" + wdid
        return rdflib.URIRef(newuri)

    def convert(self,
                records: List[Dict]):
        g = rdflib.Graph()
        for rec in records[1:]:
            # print("~~~~~~~~~~~~\n")
            rowname = self.rownamepattern
            rowuri = self._get_uri("E" + str(uuid4())[-12:])
            entities_per_column = {cn: [] for cn in self.column_classes}
            for colname, colval in rec.items():
                if len(colval) < 2:
                    continue
                # print(colname,":",colval)
                cv = colval
                linkscell = links_from_cell(colval, exclude_lists=True)
                if len(linkscell) > 0:
                    cv = linkscell[0]
                rowname = rowname.replace("{__" + colname + "__}", cv)
                # If this column corresponds to an entity
                if colname in self.column_classes:
                    col_ent_uris = []
                    if len(linkscell) > 0:
                        for lc in linkscell:
                            col_ent_uri = self._get_uri(lc)
                            col_ent_uris.append(col_ent_uri)
                            g.add((col_ent_uri,
                                   self.labelpred,
                                   rdflib.Literal(lc.replace("_", " "),
                                                  lang=self.lang)))
                    else:
                        col_ent_uri = self._get_uri("E" + str(uuid4())[-12:])
                        col_ent_label = rdflib.Literal(colval,
                                                       lang=self.lang)
                        g.add((col_ent_uri, self.labelpred, col_ent_label))
                        col_ent_uris.append(col_ent_uri)

                    for col_ent_uri in col_ent_uris:
                        g.add((col_ent_uri, rdftype, self.column_classes[
                            colname]))
                        # Links between this column and the record
                        if colname in self.row_to_oolumn_links.keys():
                            g.add((rowuri,
                                   self.row_to_oolumn_links[colname],
                                   col_ent_uri))
                        entities_per_column[colname].append(col_ent_uri)
                # If the column is not in column_classes, its a literal
                elif colname in row_to_column_links.keys():
                    g.add((rowuri,
                           self.row_to_oolumn_links[colname],
                           rdflib.Literal(colval)))

            # Intercolumn links
            for soutar, link in self.intercolumn_links.items():
                sourcecol, targetcol = soutar
                for sourcenet in entities_per_column[sourcecol]:
                    for targetent in entities_per_column[targetcol]:
                        g.add((sourcenet,
                               link,
                               targetent))

            g.add((rowuri, rdftype, self.record_class))
            g.add((rowuri, self.labelpred, rdflib.Literal(rowname,
                                                          lang=self.lang)))

        return g


with open(fnwikipediainput) as fin:
    ontns = rdflib.namespace.Namespace("https://sample.ontolog/")
    entns = rdflib.namespace.Namespace("https://en.wikipedia.org/wiki/")
    row_class = ontns["Event"]
    row_name = "Assesination of {__Target__}"
    column_classes = {
        "Target": ontns["Person"],
        "Title": ontns["Office"],
        "Place": ontns["Place"],
        "Assassin or other entity": ontns["Collective_Person"],
        "Country": ontns["Place"]
    }
    row_to_column_links = {
        "Target": ontns["hasAsVictim"],
        "Place": ontns["happenedInPlace"],
        "Assassin or other entity": ontns["hasAsPerpetrator"],
        "Date": ontns["occurredInDate"]
    }
    intercolumn_links = {
        ("Target", "Title"): ontns["holdsOfficeOf"],
        ("Target", "Country"): ontns["livedInCountry"],
        ("Place", "Country"): ontns["isLocatedIn"]
    }
    datatypes = {
        "Date": rdflib.URIRef("http://www.w3.org/2001/XMLSchema#string")
    }

    print("Starting parsing of ", fnwikipediainput)
    wl = WikimarkupDynamicList(fin.read())
    # print(str(wl))
    cols_for_links = ["Target", "Place", "Country", "Assassin or other entity"]
    links = wl.collec_links(cols=cols_for_links,
                            link_ns=entns)
    print(f"\tfound {len(links)} links")
    with open("sample_data/leaders_uris_txt", "w") as fout:
        for li in links:
            fout.write(li + "\n")
    print("\tcolumns:", wl.columns)

    print(f"Will now run converter using urimapper {mappingfile}")
    r2rdf = Records2RDF(
        record_class=row_class,
        column_classes=column_classes,
        row_to_oolumn_links=row_to_column_links,
        intercolumn_links=intercolumn_links,
        rowname_pattern=row_name,
        entity_namespace=entns,

    )
    the_kg = r2rdf.convert(wl.content)
    # print(the_kg.serialize(format="ttl"))
    print("\nA total of ", len(the_kg), "triples will be written to",
          fnttl)

    the_kg.serialize(format="ttl", destination=fnttl)

    # Now we write down the ontology

    ontology = rdflib.Graph()
    owlns = rdflib.namespace.OWL
    rdfsns = rdflib.namespace.RDFS
    rdfns = rdflib.namespace.RDF
    labelpred: rdflib.URIRef = rdflib.RDFS["label"]

    # First all the classes, each with a label
    ontology.add((ontns["ThingsDomain"], rdftype, owlns["Class"]))
    ontology.add((ontns["ThingsDomain"], labelpred, rdflib.Literal(
        "Reality", lang="en")))
    ontology.add((row_class, rdftype, owlns["Class"]))
    ontology.add((row_class, labelpred, rdflib.Literal("Event", lang="en")))
    ontology.add((row_class, rdfsns["subClassOf"], ontns["ThingsDomain"]))
    for k, v in column_classes.items():
        ontology.add((v, rdftype, owlns["Class"]))
        ontology.add((v, labelpred, rdflib.Literal(localname(v), lang="en")))
        ontology.add((v, rdfsns["subClassOf"], ontns["ThingsDomain"]))

    # Now all the links
    for k, v in row_to_column_links.items():
        ontology.add((v, labelpred, rdflib.Literal(localname(v), lang="en")))
        ontology.add((v, rdfsns["domain"], row_class))
        # Object Property
        if k in column_classes.keys():
            ontology.add((v, rdftype, owlns["ObjectProperty"]))
            ontology.add((v, rdfsns["range"], column_classes[k]))
        # Data Property
        else:
            ontology.add((v, rdftype, rdfns["Property"]))
            ontology.add((v, rdfsns["range"], datatypes[k]))

    for kk, v in intercolumn_links.items():
        dom, ran = kk
        ontology.add((v, rdftype, owlns["ObjectProperty"]))
        ontology.add((v, labelpred, rdflib.Literal(localname(v), lang="en")))
        ontology.add((v, rdfsns["range"], column_classes[ran]))
        ontology.add((v, rdfsns["domain"], column_classes[dom]))

    print(f"The ontology consists of {len(ontology)} triples and"
          f" will be written to {fnowl}")
    ontology.serialize(format="ttl",
                       destination=fnowl)

    ents = [x.n3()[1:-1]
            for x, _, _ in the_kg.triples((None,
                                           rdftype,
                                           column_classes["Target"]))][:3]

    config_dict = {
        "sparql_endpoint": "http://local_fuseki:3030/ds/query",
        "sparql_credentials": ["admin", "PleaseD0Ch4ngeTh1sN0W!"],
        "different_graphs": False,
        "ontology_path": "/config/ontology_sample.owl",
        "ontonamespace": "https://sample.ontolog/",
        "ontology_config": {
            "type_predicate": [
                rdftype.n3()[1:-1]
            ]
        },
        "openAPIExamples": {
            "entities": ents,
            "classes": [
                column_classes["Target"].n3()[1:-1]
            ],
            "default_language": "en"
        }
    }

    with open(fnconfig, "w") as fout:
        fout.write(json.dumps(config_dict, indent=1))
        print(f"The config was succesfully written to {fnconfig}")

    print("Finihsed\n\n")
