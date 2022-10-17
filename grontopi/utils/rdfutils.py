import rdflib
from typing import  Union
from pydantic import AnyUrl
from models.ontology_models import WrappedUri


def get_local_name(uri: rdflib.URIRef) -> str:
    ustr = uri.n3()[1:-1]
    if "#" in ustr:
        return ustr.split("#")[-1]
    return ustr.split("/")[-1]


def URI(uri_str) -> rdflib.URIRef:
    if type(uri_str) is rdflib.URIRef:
        return uri_str
    if (issubclass(type(uri_str), AnyUrl) or
            issubclass(type(uri_str), WrappedUri)):
        uri_str = str(uri_str)
    if uri_str[0] == "<":
        uri_str = uri_str[1:]
    if uri_str[-1] == ">":
        uri_str = uri_str[:-1]
    return rdflib.URIRef(uri_str)


def LIT(litstr: Union[rdflib.Literal, str]) -> rdflib.Literal:
    if len(litstr)==0:
        return rdflib.Literal("")
    if litstr[0] == '\"':
        litstr = litstr[1:]
    if litstr[-1] == '\"':
        litstr = litstr[:-1]
    if litstr.startswith('\\"'):
        litstr = litstr[2:]
    if litstr.endswith('\\"'):
        litstr = litstr[:-2]

    return rdflib.Literal(litstr)
