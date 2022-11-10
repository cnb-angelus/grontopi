import random as ran

from fastapi import FastAPI, Request, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from pyfiglet import Figlet

from routes import router
from config import conf as cfg


version = "0.0.3"
figlet = Figlet(font='slant')
print(figlet.renderText('GrOntoPI') + "  " + str(version))


app = FastAPI(
    title="GrOntoPI",
    description=(
        "A simple API to access reified graphs using SPARQL"),
    version=version,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(router)
