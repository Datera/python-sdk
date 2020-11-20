"""
Readers for the /api schema endpoints.  These don't request that endpoint,
they only parse the returned data
"""
import abc
import os
import re

__copyright__ = "Copyright 2017, Datera, Inc."


class EndpointSchema(object):
    def __init__(self, name, path):
        pass

    def methods():
        pass


class SchemaReader(object):

    def __init__(self, api_schema):
        self.schema = api_schema

    @abc.abstractmethod
    def parse(self):
        pass

    @abc.abstractmethod
    def get_endpoint(endpoint):
        pass

    @classmethod
    def get_reader(cls, version):
        return get_reader(version)


class Reader2(SchemaReader):
    ENTITY_RE = re.compile(r"(:\w+)")
    ENTITY_SUB = '_ENT_'
    _endpoint = '/api'

    def __init__(self, api_schema):
        super(Reader2, self).__init__(api_schema)
        self._endpoints = None
        self._entities = None
        self.parse()

    def _fix_last_en(self, path):
        return "".join(path.rsplit(self.ENTITY_SUB, 1)).rstrip("/")

    def _fix_path(self, path):
        return self.ENTITY_RE.sub(self.ENTITY_SUB, path)

    def _normalize(self, path):
        """
        Replaces all sections of the path that are not identified as endpoints
        with the ENTITY_SUB value.  This makes for a normalized view of the
        path so we can reliably compare /api schema paths with their endpoints

        Eg: /app_instances/XXXXXX-XXX-XX-XXXXX/storage_instances
                --> /app_instances/_ENT_/storage_instances
        """
        new_path = path
        bad_parts = [part for part in os.path.normpath(path).split(os.sep)
                     if part not in self._ep_name_set and part != ""]
        for part in bad_parts:
            new_path = new_path.replace(part, self.ENTITY_SUB, 1)
        return new_path

    def parse(self):
        endpoints = []
        entities = []
        # Clean stuff
        pops = []
        for ep in list(self.schema):
            if "(" in ep:
                pops.append(ep)
                body = self.schema[ep]
                newep = ep.split("(")[0]
                body['name'] = newep
                self.schema[newep] = body
                ep = newep
            if not hasattr(self.schema[ep], 'get'):
                pops.append(ep)
            if ":" in ep:
                pops.append(ep)
                body = self.schema[ep]
                newep = self._fix_path(ep)
                if 'name' in body:
                    body['name'] = self._fix_path(body['name'])
                self.schema[newep] = body
                ep = newep
        for pop in pops:
            self.schema.pop(pop)

        for ep, ep_body in self.schema.items():
            epdict = {}
            epdict['name'] = ep.split("/")[-1]
            epdict['path'] = ep
            epdict['children'] = []

            epdict['returns'] = False
            read = ep_body.get('read', None)
            if read and read.get('returnParamself.schema', None):
                epdict['returns'] = True
            if epdict['name'] == self.ENTITY_SUB:
                entities.append(epdict)
            else:
                endpoints.append(epdict)

        root_ep = {'name': 'root',
                   'path': '/',
                   'returns': False,
                   'children': []}
        for endpoint in endpoints:
            parent = "/" + "/".join(
                endpoint['path'].strip("/").split("/")[:-1])
            for other in endpoints:
                if parent == other['path']:
                    other['children'].append(endpoint['name'])
            if len(endpoint['path'].strip("/").split("/")) == 1:
                root_ep['children'].append(endpoint['name'])

        for entity in entities:
            entity['parent_path'] = (
                "/" + "/".join(entity['path'].strip("/").split("/")[:-1]))
            entity['parent'] = entity['parent_path'].split("/")[-1]
            entity['name'] = entity['parent'] + "_entity"
            for endpoint in endpoints:
                parent = "/" + "/".join(
                    endpoint['path'].strip("/").split("/")[:-1])
                if parent == entity['path']:
                    entity['children'].append(endpoint['name'])
        endpoints.append(root_ep)
        self._endpoints = {endpoint['path']: endpoint
                           for endpoint in endpoints}
        self._ep_name_set = {endpoint['name'] for endpoint in endpoints}
        for endpoint in endpoints:
            parts = endpoint['path'].split(os.sep)
            for part in parts:
                if part:
                    self._ep_name_set.add(part)
        for enum in self.get_enums():
            self._ep_name_set.add(enum)

        self._entities = {
            self._fix_last_en(entity['path']): entity for entity in entities}

    def get_enums(self):
        return self.schema[os.path.join('/system/metrics/', self.ENTITY_SUB)][
            'verbs']['read']['urlParamSchema']['metric_name']['enum']

    def get_endpoint(self, path):
        p = self._normalize(path)
        if self.ENTITY_SUB not in p:
            p = self._fix_path(p)
        return self._endpoints.get(p)

    def get_entity(self, path):
        p = self._normalize(path)
        if self.ENTITY_SUB not in p:
            p = self._fix_path(p)
        return self._entities.get(p)


class Reader21(Reader2):
    def __init__(self, api_schema):
        super(Reader21, self).__init__(api_schema)

    def get_enums(self):
        found = []
        found.extend(self.schema[os.path.join('/metrics/io', self.ENTITY_SUB)][
            'read']['urlParamSchema']['metric']['enum'])
        found.extend(self.schema[os.path.join('/metrics/hw', self.ENTITY_SUB)][
            'read']['urlParamSchema']['metric']['enum'])
        return found


class Reader22(Reader21):
    def __init__(self, api_schema):
        super(Reader22, self).__init__(api_schema)


class Reader23(Reader22):
    def __init__(self, api_schema):
        super(Reader23, self).__init__(api_schema)


def get_reader(version):
    _readers = {"v2": Reader2,
                "v2.1": Reader21,
                "v2.2": Reader22,
                "v2.3": Reader23}
    return _readers[version]
