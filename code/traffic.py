"""
Rail traffic data with accompanying methods
"""
from persist import Serializable, Multidict

__author__ = 'tomas.liden@liu.se'


class Traffic(Serializable):
    """
    The traffic data include all train services, their preferred departures, routes,
    min durations etc. In addition the time period definitions and traffic cost parameters
    are stored here
    """

    def __init__(self, periods, period_starts, period_lengths, trains, train_routes, min_link_time, min_node_time,
                 pref_dep, t_cost, d_cost, r_cost):
        Serializable.__init__(self)
        # @formatter:off
        self.periods = periods                  # range of periods          - T
        self.period_starts = period_starts      # start times per period    - b_t
        self.period_lengths = period_lengths    # period lengths            - d_t
        self.trains = trains                    # set of train services     - S
        self.train_routes = train_routes        # possible routes per train - R_s
        self.min_link_time = min_link_time      # min traversal time        - pi_sl_r
        self.min_node_time = min_node_time      # min node time             - eps_sn_r
        self.pref_dep = pref_dep                # preferred departures      - tau_s
        self.t_cost = t_cost            # duration cost for train s         - \sigma^t_s
        self.d_cost = d_cost            # deviation cost for train s        - \sigma^d_s
        self.r_cost = r_cost            # route cost per train and route    - \sigma^r_{sr}
        # @formatter:on

    def scale(self, t_fac, d_fac, r_fac):
        return Traffic(self.periods, self.period_starts, self.period_lengths, self.trains,
                       self.train_routes, self.min_link_time, self.min_node_time, self.pref_dep,
                       {k: t_fac*v for k, v in self.t_cost.items()},
                       {k: d_fac*v for k, v in self.d_cost.items()},
                       {k: r_fac*v for k, v in self.r_cost.items()})

    def node_time(self, s, n):
        return self.min_node_time[s, n] if (s, n) in self.min_node_time else 0

    def min_dur(self, s, r, route_nodes, num_links=-1):
        to = num_links if num_links > 0 else len(route_nodes) - 1
        return sum(self.min_link_time[s, r][:to]) + sum([self.node_time(s, n) for n in route_nodes[:to]])

    def periods_overlapping(self, a, b, cyclic=False):
        b_t = self.period_starts
        d_t = self.period_lengths
        min_t = b_t[0]
        max_t = b_t[-1] + d_t[-1]
        assert a <= b
        if not cyclic:
            return (t for t in self.periods if a < b_t[t] + d_t[t] and b_t[t] < b)
        else:
            h = max_t - min_t
            return (t for t in self.periods
                    if (a < b_t[t] + d_t[t] or b > max_t and b_t[t] < b - h)
                    and (b_t[t] < b or a < min_t and a + h < b_t[t] + d_t[t]))


    def __str__(self):
        return "\n".join([
            "Preferred dep : %s" % str(self.pref_dep),
            "Train routes  : %s" % str(self.train_routes),
            "Min link times: %s" % str(self.min_link_time),
            "Min node times: %s" % str(self.min_node_time),
            "Start times   : %s" % str(self.period_starts),
            "Period lengths: %s" % str(self.period_lengths),
            "Runtime cost  : %s" % str(self.t_cost),
            "Deviation cost: %s" % str(self.d_cost),
            "Route cost    : %s" % str(self.r_cost)
        ])

    def to_json(self):
        return self.rep({
            "periods": self.periods,
            "period_starts": self.period_starts,
            "period_lengths": self.period_lengths,
            "trains": self.trains,
            "train_routes": self.train_routes,
            "min_link_time": Multidict(self.min_link_time),
            "min_node_time": Multidict(self.min_node_time),
            "pref_dep": self.pref_dep,
            "t_cost": self.t_cost,
            "d_cost": self.d_cost,
            "r_cost": Multidict(self.r_cost)
        })

    @staticmethod
    def from_json(chunk):
        return Traffic(
            tuple(chunk["periods"]),
            tuple(chunk["period_starts"]),
            tuple(chunk["period_lengths"]),
            chunk["trains"],
            {k: tuple(v) for k, v in chunk["train_routes"].items()},
            {k: tuple(v) for k, v in chunk["min_link_time"].data.items()},
            chunk["min_node_time"].data,
            chunk["pref_dep"],
            chunk["t_cost"],
            chunk["d_cost"],
            chunk["r_cost"].data
        )
