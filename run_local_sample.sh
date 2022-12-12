pip install wikimapper rdflib
wget -nc https://public.ukp.informatik.tu-darmstadt.de/wikimapper/index_enwiki-20190420.db
python3 grontopi/utils/x2KG.py
chmod 777 sample_data/*ttl
docker-compose -f docker-compose-sample.yml  up