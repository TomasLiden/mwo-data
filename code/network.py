"""
The rail network data and methods for loading, saving etc
"""
from persist import Serializable, Multidict, tupleify
from random import uniform
from math import sqrt, radians, sin, cos

__author__ = 'tomas.liden@liu.se'


def _move(point, r_min, r_max, d_min, d_max):
    """
    Perform a polar move of the point, using a radius in [r_min, r_max] and a degree in |d_min, d_max]
    """
    r = uniform(r_min, r_max)
    phi = radians(uniform(d_min, d_max))
    return tuple([point[0] + r * cos(phi), point[1] + r * sin(phi)])


def dist(a, b):
    """
    Distance between two points a and b
    """
    return sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


class Nodes(dict):
    """
    A dictionary of nodes, keyed by the name and with a tuple of x, y coordinates as value.
    When adding nodes they are checked for overlapping and adjusted so as to get a clear plotting.
    The x, y coordinates are given in the [0, 1] range
    """
    def add(self, name, point=None, placement=0):
        if not point:
            if placement == 0:
                point = (uniform(0, 1), uniform(0, 1))
            elif placement < 0:
                point = _move((0.5, 0.5), 0.2, 0.4, 120, 240)
            else:
                point = _move((0.5, 0.5), 0.2, 0.4, -60, 60)
        i = 0
        while i < 5 and self.overlap(point):
            point = _move(point, 0.1, 0.1, 0, 360)
        assert not self.overlap(point), "Node %s still overlaps others after trying to adjust: (%.4f, %.4f)" % \
                                        (name, point[0], point[1])
        self[name] = point

    def overlap(self, point):
        for n in self.itervalues():
            if dist(n, point) < 0.01:
                return True
        return False

    def __str__(self):
        return str({k: (round(v[0], 4), round(v[1], 4)) for k, v in self.items()})


class Network(Serializable):
    """
    A rail network with nodes, links, capacities (over links) and routes together with:
    - route_links: links per route (L_r)
    - route_nodes: nodes in route r (N_r)
    - route_dirs: travel dir. per route (d_l for l in L_r)
    """

    def __init__(self, nodes, links, routes, capacity, route_links, route_nodes, route_dirs):
        Serializable.__init__(self)
        self.nodes = nodes
        self.links = links
        self.routes = routes
        self.capacity = capacity
        self.route_links = route_links
        self.route_nodes = route_nodes
        self.route_dirs = route_dirs

    def od_routes(self):
        # find all OD pairs and their possible routes
        od_r = {}
        cancellation = False
        for r, nodes in self.route_nodes.items():
            if len(nodes):
                k = (nodes[0], nodes[-1])
                if k not in od_r:
                    od_r[k] = []
                od_r[k].append(r)
            else:
                cancellation = r
        if cancellation:
            od_r = {k: rl + [cancellation] for k, rl in od_r.items()}
        return od_r

    def single_track(self, l):
        return l in self.capacity and self.capacity[l][1] < 2 * self.capacity[l][0]

    def __str__(self):
        return "\n".join([
            "Nodes: %s" % str(self.nodes),
            "Links: %s" % str(self.links),
            "Normal cap : %s" % self.capacity,
            "Route nodes: %s" % self.route_nodes,
            "Route links: %s" % self.route_links,
            "Route dirs : %s" % self.route_dirs
        ])

    def to_json(self):
        return self.rep({
            "nodes": self.nodes,
            "links": self.links,
            "routes": self.routes,
            "capacity": Multidict(self.capacity),
            "route_links": self.route_links,  # dict will be stored as list
            "route_nodes": self.route_nodes,  # -"-
            "route_dirs": self.route_dirs  # -"-
        })

    @staticmethod
    def from_json(chunk):
        return Network(
            chunk["nodes"],
            tupleify(chunk["links"]),
            chunk["routes"],
            {k: tuple(v) for k, v in chunk["capacity"].data.items()},
            {k: tupleify(v) for k, v in chunk["route_links"].items()},
            {k: tuple(v) for k, v in chunk["route_nodes"].items()},
            {k: tuple(v) for k, v in chunk["route_dirs"].items()}
        )
