import base64
import json
import string

from ioc_finder import find_iocs

from machina.core.worker import Worker

def _strings(data, min=4):
    result = ""
    for c in data:
        if c in string.printable:
            result += c
            continue
        if len(result) >= min:
            yield result
        result = ""
    if len(result) >= min:  # catch result at EOF
        yield result

class FindURLs(Worker):

    types_blacklist = ['url']
    next_queues = ['Identifier']

    def __init__(self, *args, **kwargs):
        super(FindURLs, self).__init__(*args, **kwargs)

    def callback(self, data, properties):
        data = json.loads(data)

        # resolve path
        target = self.get_binary_path(data['ts'], data['hashes']['md5'])

        with open(target, 'r', errors="ignore") as f:
            strings = ' '.join(_strings(f.read()))

        urls = find_iocs(strings)['urls']

        self.logger.info(f"found urls: {urls}")

        # get the appropriate OGM class for the object that was analyzed
        obj_cls = self.resolve_db_node_cls(data['type']) 
        obj = obj_cls.nodes.get(uid=data['uid'])

        # For each URL, resubmit the URL to Identifier and
        # manually type it as 'url'
        for url in urls:
            data_encoded = base64.b64encode(url.encode()).decode()
            body = json.dumps(
                {
                    'data': data_encoded,
                    'origin': {
                        'ts': data['ts'],
                        'md5': data['hashes']['md5'],
                        'uid': data['uid'],
                        'type': data['type']
                    },
                    'type': 'url'
                }
            )
            self.publish_next(body)

