from typing import List
import requests
import json
import itertools as it

class Graph2Text: 
    def __init__(self, **args) -> None:
        self.api = args['g2t_api']
        # self.__dict__.update(args)

    def _preprocess(self, amrs):
        # Do preprocessing
        pass

    def _posprocess(self, doc: str):
        # Do posprocessing 
        doc = json.loads(doc)
        docs = doc['data']
        docs = [_['snt'] for _ in docs]

        # docs = list(it.chain(docs))
        docs = ' '.join(docs)
        print(docs)
        return docs

    def g2t(self, amrs: List[str]):
        # _preprocess(amr)

        payload = json.dumps({'amr_texts': amrs, "linearized": False })
        headers = {
        'Content-Type': 'application/json'
        }

        response = requests.request("POST", self.api, headers=headers, data=payload)
        resp_json, resp_cod = response.text, response.status_code

        if resp_cod==200:
            resp_txt = self._posprocess(resp_json)
            return resp_txt

