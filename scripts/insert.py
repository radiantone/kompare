from datetime import datetime
from elasticsearch import Elasticsearch
es = Elasticsearch(hosts=['https://elastic:DkIedPPSCb@localhost:9200'],verify_certs=False)

doc = {
    'author': 'kimchy',
    'text': 'Elasticsearch: cool. bonsai cool.',
    'timestamp': datetime.now(),
    'id':12345
}
resp = es.index(index="test-index", id=12345, document=doc)
print(resp['result'])

resp = es.get(index="test-index", id=12345)
print(resp['_source'])

es.indices.refresh(index="test-index")

resp = es.search(index="test-index", query={"match_all": {}})
print("Got %d Hits:" % resp['hits']['total']['value'])
for hit in resp['hits']['hits']:
    print("%(timestamp)s %(author)s: %(text)s" % hit["_source"])
