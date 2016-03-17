"""
The rail network data and methods for loading, saving etc
"""
from persist import Serializable, Multidict, tupleify, names
from random import uniform, normalvariate
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


def generate_line(num_nodes, stddev, div, cap):
    nodes = Nodes()
    links = []
    capacity = {}
    # Create nodes and links with varying length
    s = 0.0
    nodelist = names('N', 0, num_nodes)
    for i in range(0, num_nodes):
        s0, s = s, i * 1.0 / (num_nodes - 1)
        s += (i in range(1, num_nodes - 1)) * normalvariate(0, stddev / num_nodes)
        assert s >= s0, "Negative link length - probably too large variance (p0) value..."
        curr = nodelist[i]
        nodes.add(curr, (s, 0.0))
        if i:
            link = (nodelist[i - 1], curr)
            links.append(link)
            capacity[link] = cap
    # Create routes
    routes = {nodelist[0] + '-' + nodelist[-1]: tuple(nodelist), '0': ()}
    prev = nodelist[0]
    n0 = 0
    for p in range(div - 1):
        n1 = n0 + int(round((num_nodes - 1) / div + uniform(0, 1)))
        curr = nodelist[n1]
        routes[prev + '-' + curr] = tuple(nodelist[n0: n1 + 1])
        n0 = n1
        prev = curr
    if n0 > 0:
        routes[prev + '-' + nodelist[-1]] = tuple(nodelist[n0: num_nodes])
    return Network.from_routes(routes, capacity, nodes, set(links))


def generate_network():
    nodes = Nodes({'N1': (0.0, 0.5), 'N2': (0.2, 0.4),
                   'N3': (0.4, 0.3), 'N4': (0.5, 0.4),
                   'N5': (0.8, 0.2), 'N6': (1.0, 0.0),
                   'N7': (0.1, 0.1), 'N8': (0.8, 0.5)})
    routes = {'1-3-6': ('N1', 'N2', 'N3', 'N5', 'N6'),
              '1-4-6': ('N1', 'N2', 'N4', 'N5', 'N6'),
              '7-8': ('N7', 'N3', 'N4', 'N8'),
              '0': ()}
    single = (3, 5)
    double = (4, 8)
    capacity = {('N1', 'N2'): double,
                ('N2', 'N3'): single,
                ('N3', 'N5'): single,
                ('N5', 'N6'): double,
                ('N2', 'N4'): single,
                ('N4', 'N5'): single,
                ('N3', 'N7'): single,
                ('N3', 'N4'): single,
                ('N4', 'N8'): single
                }
    return Network.from_routes(routes, capacity, nodes)



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

    @staticmethod
    def from_routes(routes, capacity, nodes=None, links=set()):
        """
        Setting up data structures. If nodes and links are not given they will be derived from the route data.
        :param routes: dictionary of {name: tupleOfNodes} entries
        :param capacity: dictionary of {link: (trackCap=int, linkCap=int)} entries,
        where trackCap is for one direction and linkCap is sum for both directions
        :param nodes (optional) dictionary of {name: tupleOfXyCoordinates} - i.e. map coordinates keyed by node name
        :param links: (optional) set of node name tuples (fromNode, toNode) where fromNode < toNode
        """
        if not nodes:
            nodes = Nodes()
        route_links = {}
        route_nodes = {}
        route_dirs = {}
        for name, node_list in routes.items():
            assert len(node_list) == 0 or len(node_list) > 1, "Invalid number of nodes in route " + name
            if len(node_list) > 1:
                for n in node_list[0], node_list[-1]:
                    if n not in nodes:
                        placement = -1 if n == node_list[0] else 1
                        nodes.add(n, None, placement)
                num_intermediate = len(node_list) - 2
                p0 = nodes[node_list[0]]
                p1 = nodes[node_list[-1]]
                for i, n in enumerate(node_list[1:-1]):
                    if n not in nodes:
                        a = float(i + 1) / (num_intermediate + 1)
                        x = (1 - a) * p0[0] + a * p1[0]
                        y = (1 - a) * p0[1] + a * p1[1]
                        nodes.add(n, (x, y))
            rl = []  # the links in the route
            rd = []  # the travel directions for each link
            # Construct the links
            for i in range(len(node_list) - 1):
                assert node_list[i] != node_list[i + 1], \
                    "Route " + name + " error: Link cannot start and end in same node " + node_list[i]
                d = int(node_list[i] < node_list[i + 1])
                rl.append((node_list[i + 1 - d], node_list[i + d]))
                rd.append(d)
            rl = tuple(rl)
            links.update(rl)
            route_nodes[name] = node_list
            route_links[name] = rl
            rev_name = '-'.join(reversed(name.split('-')))
            route_nodes[rev_name] = node_list[::-1]
            route_links[rev_name] = tuple(rl[::-1])
            route_dirs[name] = tuple(rd)
            route_dirs[rev_name] = tuple([1 - i for i in rd[::-1]])
        for l in links:
            assert l[0] in nodes and l[1] in nodes, "Link data for %s not in node list.." % (l,)
            assert l[0] < l[1], "Nodes given in incorrect order for link %s" % (l,)
        for l in capacity:
            assert l in links, "Capacity given for non-existing link %s" % (l,)
        return Network(nodes, tuple(links), routes, capacity, route_links, route_nodes, route_dirs)

    @staticmethod
    def generate(dat):
        if not dat:
            return False
        arg = dat.split(':')
        nw_type = arg[0]
        if nw_type[0] == 'l':
            size = int(arg[1])
            p0 = float(arg[2])
            p1 = int(arg[3])
            c_dat = arg[4].split(',')
            cap = (int(c_dat[0]), int(c_dat[1]))
            return generate_line(size, p0, p1, cap)
        elif nw_type[0] == 't':
            pass
        elif nw_type[0] == 'n':
            return generate_network()

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
