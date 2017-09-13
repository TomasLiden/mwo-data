"""
Resource data for maintenance crew considerations
"""
from persist import Serializable, tupleify

__author__ = 'tomas.liden@liu.se'


class Resources(Serializable):
    def __init__(self, bases, base_links, base_crew, limits, costs):
        Serializable.__init__(self)
        self.bases = bases
        self.base_links = base_links  # the links covered by maintenance crew in base b
        self.base_crew = base_crew  # the set of crews belonging to base b
        self.limits = limits  # the resource limitations (max work length, min rest time etc)
        self.costs = costs  # cost factors
        # derived sets
        self.all_crew = sorted(set(c for b in bases for c in base_crew[b]))  # same K
        all_links = sorted(set(l for b in bases for l in base_links[b]))  # should be same as L^M
        self.crews = {}  # crews[l] same as K_l
        self.links = {}  # links[k] same as L_k
        for l in all_links:
            possible_bases = [b for b in bases if l in base_links[b]]
            self.crews[l] = sorted(set(c for b in possible_bases for c in self.base_crew[b]))
        for k in self.all_crew:
            self.links[k] = list(l for l in all_links if k in self.crews[l])
        # provide attributes for convenience (and safeguarding that these values really exist)
        self.max_work = self.limits['max_work']
        self.min_rest = self.limits['min_rest']
        self.cyclic = self.limits["cyclic"]
        self.crew_cost = self.costs["crew_cost"]
        self.work_cost = self.costs["work_cost"]
        self.link_cost = self.costs["link_cost"] if "link_cost" in self.costs else 0

    def __str__(self):
        return "\n".join([
            "Bases      : %s" % str(self.bases),
            "Base links : %s" % str(self.base_links),
            "Base crew  : %s" % str(self.base_crew),
            "Limits     : %s" % str(self.limits),
            "Costs      : %s" % str(self.costs),
            "Crews[l]   : %s" % str(self.crews),
            "Links[k]   : %s" % str(self.links)
        ])

    def to_json(self):
        return self.rep({
            "bases": self.bases,
            "base_links": self.base_links,
            "base_crew": self.base_crew,
            "limits": self.limits,
            "costs": self.costs
        })

    @staticmethod
    def from_json(chunk):
        return Resources(
            chunk["bases"],
            {k: tupleify(v) for k, v in chunk["base_links"].items()},
            chunk["base_crew"],
            chunk["limits"],
            chunk["costs"]
        )
