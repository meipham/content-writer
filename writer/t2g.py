from typing import List, Tuple
import requests
import json
import http.client
import json

class Text2Graph: 
    def __init__(self, **args) -> None:
        self.api = args['t2g_api']
        self.__dict__.update(args)
        
    def _preprocess(self, doc):
        # Do preprocessing
        pass

    def _posprocess(self, doc) -> List[str]:
        # Do posprocesing 
        snts = json.loads(doc)["article"]
        amrs = [_['amr'] for _ in snts]
        return amrs

    def t2g(self, text) -> List[str]:
        payload = json.dumps({"text": text})
        headers = {
        'Content-Type': 'application/json'
        }
        response = requests.request("POST", self.api, headers=headers, data=payload)

        resp_json, resp_cod = response.text, response.status_code
        if resp_cod == 200:
            amrs = self._posprocess(resp_json)
            return amrs
        