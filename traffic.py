"""
Rail traffic data with accompanying methods
"""
from persist import Serializable, Multidict, names
from random import uniform, normalvariate
from network import dist

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

    @staticmethod
    def from_traindata(time_list, train_data, network):
        """
        Setting up the data structures
        :param time_list: a sequence of time points
        :param train_data: a dictionary with train-id as key. The data consists of:
        1) a preferred departure time;
        2) runtime and deviation cost;
        3) a set of possible routes (key), with 3a) route cost and 3b) min traversal times over the links; and
        4) traversal time (if other than zero) over nodes.
        :param network (class Network): the rail network for which to run the traffic
        """
        trains = train_data.keys()
        # Definition of time periods given as a list of nrT - 1 (clock) times
        # -> start_times and period_lengths
        periods = range(len(time_list) - 1)
        period_starts = time_list[:-1]
        period_lengths = tuple([time_list[i + 1] - time_list[i]
                                for i in range(len(time_list) - 1)])
        train_routes = {}
        min_link_time = {}
        min_node_time = {}
        pref_dep = {}
        t_cost = {}
        d_cost = {}
        r_cost = {}
        for s, (dep, (t_cost[s], d_cost[s]), r_s, n_t) in train_data.items():
            pref_dep[s] = dep
            train_routes[s] = tuple(r_s.keys())
            for n, dur in n_t.items():
                min_node_time[s, n] = dur
            for r, (r_cost[s, r], min_times) in r_s.items():
                assert r in network.route_links, \
                    "Train " + s + " has an undefined route: " + r
                r_len = len(network.route_links.get(r))
                assert len(min_times) == r_len, \
                    "Incorrect number of traversal times in route %s for train %s, should be %i" % (r, s, r_len)
                min_link_time[s, r] = min_times
                t1 = dep + sum(min_times) + sum(min_node_time.get((s, n), 0) for n in network.route_nodes[r])
                assert time_list[0] <= dep and t1 < time_list[-1], \
                    "Wanted timing [%.2f, %.2f] for train %s along route %s not within planning period [%.2f, %.2f]" \
                    % (dep, t1, s, r, time_list[0], time_list[-1])
            start_nodes = set(network.route_nodes[r][0] for r in r_s if network.route_nodes[r])
            end_nodes = set(network.route_nodes[r][-1] for r in r_s if network.route_nodes[r])
            if len(start_nodes) > 1 or len(end_nodes) > 1:
                print "WARNING: Train %s starts/ends at more than place?! Start/end nodes: %s/%s" % \
                      (s, start_nodes, end_nodes)
        return Traffic(periods, period_starts, period_lengths,
                       trains, train_routes, min_link_time, min_node_time, pref_dep,
                       t_cost, d_cost, r_cost)

    @staticmethod
    def generate(nw, dat):
        if not nw or not dat:
            return False
        arg = dat.split(':')
        nt = int(arg[0])
        p0 = float(arg[2])
        p1 = float(arg[3])
        periods = range(nt)
        period_starts = range(1, nt + 1)
        period_lengths = [1] * len(periods)
        od_routes = nw.od_routes()
        if ',' not in arg[1]:
            ns = [int(arg[1])] * len(od_routes)
        else:
            ns = [int(i) for i in arg[1].split(',')]
        assert len(ns) == len(od_routes), "Must specify nr of train services (ns) for each OD relation"
        trains = names('S', 0, sum(ns))
        train_routes = {}
        pref_dep = {}
        min_link_time = {}
        min_node_time = {}
        t_cost = {}
        d_cost = {}
        r_cost = {}
        si = 0
        # Treat the OD in the order of their names
        for od_ix, od in enumerate(sorted(od_routes.keys())):
            routes = od_routes[od]
            link_times = {}
            travel_time = 0
            for r in routes:
                link_times[r] = [p1 * dist(nw.nodes[a], nw.nodes[b])
                                 for a, b in nw.route_links[r]]
                travel_time = max(travel_time, sum(link_times[r]))
            # This will spread the trains roughly evenly over the period
            # Might consider allowing them to be grouped more (by having dep0/1 in (b_t[0], b_t[-1]))
            dep0 = uniform(period_starts[0], period_starts[1])
            dep1 = uniform(period_starts[-1], period_starts[-1] + period_lengths[-1]) - travel_time
            num_od_trains = ns[od_ix]
            for i in range(num_od_trains):
                s = trains[si]
                train_routes[s] = tuple(routes)
                pref_dep[s] = dep0 + i * (dep1 - dep0) / (num_od_trains - 1)
                # variate the dep for intermediate trains
                pref_dep[s] += (i in range(1, num_od_trains - 1)) * normalvariate(0, p0)
                si += 1
                for r in routes:
                    min_link_time[s, r] = link_times[r]
                    # using min_node_time = 0 (default value)
                    r_cost[s, r] = 1 if len(link_times[r]) > 0 else 10
                t_cost[s] = 1
                d_cost[s] = 0.1
        return Traffic(periods, period_starts, period_lengths,
                       trains, train_routes, min_link_time, min_node_time, pref_dep,
                       t_cost, d_cost, r_cost)

    def node_time(self, s, n):
        return self.min_node_time[s, n] if (s, n) in self.min_node_time else 0

    def min_dur(self, s, r, route_nodes, num_links=-1):
        to = num_links if num_links > 0 else len(route_nodes) - 1
        return sum(self.min_link_time[s, r][:to]) + sum([self.node_time(s, n) for n in route_nodes[:to]])

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
