#!/usr/bin/env python
"""
Methods and classes for handling persistence of data objects
"""
import inspect
import json
from math import ceil, log10

__author__ = 'tomas.liden@liu.se'


class Serializable:
    """
    Stub class for non-standard objects to be serialized with JSON
    """
    def __init__(self):
        pass

    def to_json(self):
        """
        Return a representation that is serializable by JSON, using the following code stub
        return self.rep({k1: v1, k2: v2})
        """
        raise NotImplementedError

    def rep(self, r):
        """
        Wrapper method for adding the class name to the object representation,
        which will be used by _decoder() to retrieve the appropriate class type.
        """
        assert isinstance(r, dict), "The representation must be given as a dict"
        # note for the future: using self.__class__ causes a ref to the class object which json.dump
        # will try to serialize. But then there is no callable to_json() method
        r.update({"__class__": self.__class__.__name__})
        return r

    @staticmethod
    def from_json(chunk):
        """
        Return a class object from the chunk coming from JSON
        """
        raise NotImplementedError


class Multidict(Serializable):
    """
    Wrapper class for dictionaries with multiple (tuple) keys
    Needed since JSON only support strings as keys
    """

    def __init__(self, md):
        Serializable.__init__(self)
        self.data = md

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.data)

    def to_json(self):
        o = self.rep({"items": self.data.items()})
        return o

    @staticmethod
    def from_json(chunk):
        md = dict([(tupleify(k), v) for k, v in chunk["items"]])
        return Multidict(md)


def tupleify(d):
    if isinstance(d, list):
        return tuple(tupleify(e) for e in d)
    else:
        return d


class _Encoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Serializable):
            return o.to_json()
        raise TypeError(str(o) + ' is not JSON serializable')


def json_dumps(obj):
    return json.dumps(obj, cls=_Encoder, sort_keys=True)


def json_dump(obj, fp):
    json.dump(obj, fp, cls=_Encoder, sort_keys=True, indent=2)


def register(types):
    """
    Register the serializable classes.
    Will add Multidict if it's not given in types
    :param types: list of types, e.g. globals().values(), locals().values(), [Multidict, ...]
    """
    global serializableClasses
    serializableClasses = {c.__name__: c
                           for c in types if inspect.isclass(c) and issubclass(c, Serializable)}
    if "Multidict" not in serializableClasses:
        serializableClasses[Multidict.__name__] = Multidict


serializableClasses = {}


def _decoder(chunk):
    assert len(serializableClasses) > 0, "No serializable classes known - must call register(types) before decoding"
    chunk = _byteify(chunk)
    if "__class__" in chunk and chunk["__class__"] in serializableClasses:
        return serializableClasses[chunk["__class__"]].from_json(chunk)
    return chunk


def _byteify(d):
    """
    Transform unicode (from JSON) into normal python byte strings
    :param d: raw decoded json object (from json.load/loads)
    :return: recursive byte transformation of d
    """
    if isinstance(d, dict):
        return {_byteify(key): _byteify(value) for key, value in d.iteritems()}
    elif isinstance(d, list):
        return [_byteify(element) for element in d]
    elif isinstance(d, unicode):
        return d.encode('utf-8')
    else:
        return d


def json_loads(s):
    return json.loads(s, object_hook=_decoder)


def json_load(f):
    return json.load(f, object_hook=_decoder)


def names(prefix, fr, to):
    w = int(ceil(log10(to - fr)))
    return [prefix + str(i).zfill(w) for i in range(fr, to)]


if __name__ == "__main__":
    md1 = Multidict({(1, 2): 12, (3, 4): 34})
    md2 = Multidict({(5, 6): 'Aa'})
    dump = json_dumps([md1, md2])
    print dump
    register(locals().values())  # or register([Multidict])
    ml = json_loads(dump)
    print ml
