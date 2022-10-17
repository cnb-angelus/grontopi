from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends
from fastapi import HTTPException

from models.api_models import EntityDescription
from models.api_models import EntityListWithLabels
from models.ontology_models import EntityURI, ClassURI
from utils.OAuth2_serverside import user_invalidator
from data_access import SPARQLAccess
from utils.owlreading import OntologyReader
from config import conf as cfg

router = APIRouter()
onto = OntologyReader(ontologypath=cfg.ontology_path,
                      config_object=cfg)
graph = SPARQLAccess(query_endpoint=cfg.sparql_endpoint,
                     query_credentials=cfg.sparql_credentials,
                     )


@router.get(
    "/static_schemas", tags=["Vocabularies"],
    description=(
            "Catalogs, Relations and Classes (see description of "
            "respective outputs)")
)
async def catalogs_ontology(user_info: str = Depends(user_invalidator())):
    stime = datetime.now()
    cats = onto.get_catalogues()
    clss = onto.get_study_domain_classes()
    rels = onto.get_relations()
    props = onto.get_properties()
    response = {
        "message": "OK", "catalogs": cats, "classes": clss, "relations": rels,
        "properties": props}
    dt = datetime.now() - stime
    print(
        f"\n\n---- Finished static schemas {dt.total_seconds()}     <-")
    return response


@router.get(
    "/entities/by_id", tags=["Statements"],
    response_model=EntityDescription)
async def entities_by_id(entity_id: EntityURI,
                         user_info: str = Depends(user_invalidator())):
    res = graph.fetch_entities_from_list_of_ids(entitylist=[entity_id])
    if res is None or not res or res[0] is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    res = res[0]

    if isinstance(res, dict):
        if not any(
                (res["data_properties"],
                 res["object_properties"], res["inverse_properties"])):
            raise HTTPException(status_code=404, detail="Entity not found")
        return res

    return res


@router.post(
    "/entities/by_ids",
    tags=["Statements"],
    response_model=List[EntityDescription])
async def entities_by_ids(entity_ids: List[EntityURI],
                          user_info: str = Depends(user_invalidator())):
    res = graph.fetch_entities_from_list_of_ids(entitylist=entity_ids)
    if res is None or len(res) == 0:
        raise HTTPException(status_code=404, detail="Entity not found")

    return res


@router.get(
    "/entities/by_class_with_labels", tags=["Statements"],
    response_model=EntityListWithLabels)
async def entities_labels(class_id: ClassURI,
                          start: int = 0, per_page: int = 100,
                          lang: str = "en",
                          user_info: str = Depends(user_invalidator())):
    res = graph.fetch_entities_of_classes(class_id=class_id,
                                          start=start, per_page=per_page,
                                          lang=lang)
    return res


@router.get("/entitites/connected_to", tags=["Statements"])
async def entities_connected_to(central_entity: EntityURI,
                                user_info: str = Depends(user_invalidator())):
    chk = graph.check_existence_of_entities([central_entity])
    if len(chk) > 0:
        raise HTTPException(
            status_code=400,
            detail={"message": "Entity does not exist", "entities": chk})
    res = graph.fetch_entities_around(entity_id=central_entity)

    return res
