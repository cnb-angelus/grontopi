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
   `docker run --rm --name grafo -e  LOG_LEVEL=info -p 8000:80 -v $(pwd)/config:/config -it grontopi`
4. You can then find the API documentation at http://localhost:8000/api/docs


### Running for development
You can follow these steps if you want to alter the code and have the hot
reload functionality of gunicorn make your life easier:
 1. Build your container `docker-compose -f docker-compose-dev.yml build`
 2. Run it ` docker-compose -f docker-compose-dev.yml up`
 3. Access the OpenAPI docs at http://localhost:8000/docs
 4. Make changes to your code (all inside the ./grontopi dir)
 5. See how it automatically reloads

### Running in a more productive environment
We will develop a docker-compose file with an example UI and triplestore.

---

## Configuring

Configuration of the application is done in the following sequence:
1. The default, built-in, configs are set. These are coded into the 
   `grontopi/config.py` file and correspond to a Wikidata example for 
   painters, writers and galleries.
2. From the config json (described below), whose location is 
   `/config/config.json` by default, but can also be specified by the env 
   variable `CONFIG_PATH`. In the examples above and in the docker-compose, 
   this file is mounted from the host into the default location.
   
### The config.json file
The file `config/example.json` included in this repository shows all the 
variables that you can set, each with their default value. 
Configuration is divided into three sections

#### General (root of json)
* `sparql_endpoint`: The URL of a [SPARQL 1.1](https://www.w3.org/TR/sparql11-query/) endpoint for the graph
* `sparql_credentials` : a list whose two elements are, respectively, the 
  username and password for Basic authentication into the endpoint
* `different_graphs`: a boolean. If True, then all SPARQL queries will be 
  enclosed in a `GRAPH ?g {.....}` block, allowing for results to come from 
  different graphs. Some endpoints (e.g. Wikidata's blazegraph) do not 
  support this syntax
*  `ontology_path` : A filesystem path of where an [OWL](https://www.w3.org/TR/2012/REC-owl2-primer-20121211/) file describing
the ontology that the graph follows. The file can be in any of the RDF 
   serializations supported by default by RDFLib. 
   
    **Note that the ontology need not describe the whole graph, but only 
   the part that will queried using GrOntoPI.** Thus, as you will see in 
   the example, you can describe only some classes and some properties 
   among them that you which to visualize. When building this OWL file, we 
   recommend to start with the minimun number of classes needed and grow 
   from there, as starting with a whole, complex ontology like Wikidata or 
   DBPedia hasn't been tested yet.
   
* `ontonamespace` : The namespace prefix of the ontology predicates that 
  will be used in the next section. This means that all values from the 
  ontology_config section will be treated as localnames for this namespace, 
  except if they contain the string `://` in which case they will be 
  treated as URIs. 
  
#### ontology_config
* `study_domain_class` : the class that will be treated as the class of all 
  domain things. All classes in the ontology must be rdf:subclasses of this 
  class.
  
* `label_uris` : A list that denotes the predicates use to assign 
  labels to entities. For example `skos:prefLabel`, `skos:altLabel` and 
  `rdfs:Label`
  
* `type_predicate` : A list that denotes the predicates use to assign 
  types to entities. In theory, this should be `[rdf:Type]` but some 
  graphs (like Wikidata) use their own predicates for types, such as `wdt:P31`.
  
  Note that for your particular usecase, more than one property might be 
  relevant. For example, if one wants to visualize painters from Wikidata, 
  one must put here the [occupation](https://www.wikidata.org/wiki/Property:P106) 
  property from the WIkidata Ontology. If your graph is a thesaurus, you 
  might want to use `skos:narrower` here.
  
#### oauth2_config
This section includes configuration to make this API check for the validity 
of JWT tokens issued by an OAuth2 identity provider. This config is used 
only for authentication purposes, as any claims on the token are not 
checked against. If you wish to further configure this, feel free to 
customize the `utils/OAuth2_serverside.py` file, in particular the 
`user_invalidator` decorator. Currently only RSA signatures for tokens are 
supported. 

* `use_OAuth2` : whether to check for JWT tokens, default false in every 
  request.
* `auth_server_kid` : the Key ID of the server, used to validate the signature
* `auth_sever_n`: the public key to verify token signature
* `interservices_token` : if the token sent is equal to 
  `{conf.interservices_token}={conf.auth_server_kid}` then then token is 
  deemed valid, without signature verification. This is a way to provide 
  static tokens, for example, for other services to use GrOntoPI.

#### openAPIExamples
These configs are used to generate the OpenAPI examples that will be 
available on the server.
* `entities` : a list of URIs of entities known to be in the graph
* `classes` : a set of classes known to be in the graph
* `default_language` : the language to use to get the labels (default `en`) 


---

## Contributors:
This project was developed as part of Project Angelus. Funded by CONACYT
(Mexican Ministry of Science) under grant 321368.

Main contributors are:
* Victor Mireles
* Eduardo Herrera
