from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends
from fastapi import HTTPException
from pydantic import parse_obj_as

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
                     query_credentials=cfg.sparql_credentials)

exent = cfg.openAPIExamples["entities"][0]
exents = cfg.openAPIExamples["entities"]
excls = cfg.openAPIExamples["classes"][0]
deflang = cfg.openAPIExamples["default_language"]

@router.get(
    "/static_schemas", tags=["Vocabularies"],
    description=(
            "Catalogs, Relations and Classes (see description of "
            "respective outputs)")
)
async def catalogs_ontology(
        #user_info: str = Depends(user_invalidator())
        ):
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
async def entities_by_id(entity_id: EntityURI = exent,
                         lang: str = deflang,
                         #user_info: str = Depends(user_invalidator())
                         ):
    res = await graph.fetch_entities_from_list_of_ids(entitylist=[entity_id],
                                                      onto=onto,
                                                      lang=lang
                                                      )
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
async def entities_by_ids(entity_ids: List[EntityURI] = exents,
                          lang: str = deflang,
                          #user_info: str = Depends(user_invalidator())
                          ):
    res = await graph.fetch_entities_from_list_of_ids(entitylist=entity_ids,
                                                      onto=onto,
                                                      lang=lang)

    if res is None or len(res) == 0:
        raise HTTPException(status_code=404, detail="Entity not found")

    return res


@router.get(
    "/entities/by_class_with_labels", tags=["Statements"],
    response_model=EntityListWithLabels)
async def entities_labels(class_id: ClassURI = excls,
                          start: int = 0, per_page: int = 100,
                          lang: str = deflang,
                          #user_info: str = Depends(user_invalidator())
                          ):
    res = graph.fetch_entities_of_classes(class_id=class_id,
                                          start=start, per_page=per_page,
                                          lang=lang)
    return res


@router.get("/entitites/connected_to", tags=["Statements"])
async def entities_connected_to(central_entity: EntityURI = exent,
                                lang : str = deflang,
                                #user_info: str = Depends(user_invalidator())
                                ):
    chk = await graph.check_existence_of_entities([central_entity],
                                            onto_config=onto)
    if len(chk) > 0:
        raise HTTPException(
            status_code=400,
            detail={"message": "Entity does not exist", "entities": chk})
    res = await graph.fetch_entities_around(entity_id=central_entity,
                                      lang=lang,
                                      onto_config=onto)

    return res
