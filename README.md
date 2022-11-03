# GrOntoPI

GrOntoPI is a simple web API for querying ontology-based graphs. It converts
 the results of, e.g. SPARQL queries to a triplestore, into nice JSON objects
 that can help frontend present the graph. These objects contain a
 combination of the data plus the ontology behind the graph.

 In theory, one would only need to configure this with the ontology of
 interest and select from it a couple of properties (e.g. what properties
 denote labels). Then, one can just point it to a SPARQL endpoint containing
 data that abides to the ontology, and everything should work.

## Running

### Simple execution

1. First build the docker continer using `docker build -t grontopi .`
2. Then put your config file and ontology (an owl file) in `./config`
3. Finally launch the container with 
   `docker run --rm --name grafo -e  LOG_LEVEL=info -p 8000:80 -v "$(pwd)/config:/config" -it grontopi`
4. You can then find the API documentation at http://localhost:8000/api/docs


### Running for development
You can follow these steps if you want to alter the code and have the hot
reload functionality of gunicorn make your life easier:
 1. Build your container `docker-compose -f docker-compose-dev.yml build`
 2. Run it ` docker-compose -f docker-compose-dev.yml up`
 3. Access the docs at http://localhost:8000/docs
 4. Make changes to your code (all inside the ./grontopi dir)
 5. See how it automatically reloads

### Running in a more productive environment
We will develop a docker-compose file with an example UI and triplestore.

--- 

## Contributors:
This project was developed as part of Project Angelus. Funded by CONACYT
(Mexican Ministry of Science) under grant 321368.

Main contributors are:
* Victor Mireles
* Eduardo Herrera
