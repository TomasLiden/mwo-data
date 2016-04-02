"""
Train sets for scheduling periods, possible links and train directions per link
"""
__author__ = 'tomas.liden@liu.se'


class TrainSets:
    def __init__(self, periods, links, dirs_over):
        self.periods = periods
        self.links = links
        self.dirs_over = dirs_over

    @staticmethod
    def setup(network, traffic, dt):
        nw = network
        tr = traffic
        b_t = tr.period_starts
        d_t = tr.period_lengths
        tr_periods = {}
        tr_links = {}
        tr_dirs = {}
        for s in tr.trains:
            dur = max([tr.min_dur(s, r, nw.route_nodes[r]) for r in tr.train_routes[s]])
            lb = tr.pref_dep[s] - dt
            ub = tr.pref_dep[s] + dur + dt
            tr_periods[s] = [t for t in tr.periods if b_t[t] < ub and b_t[t] + d_t[t] > lb]

            tr_links[s] = set(l for r in tr.train_routes[s] for l in nw.route_links[r])
        for l in nw.links:
            train_dirs_over_l = {}
            routes_over_l = [r for r in nw.route_links if l in nw.route_links[r]]
            for s in tr.trains:
                dirs_over_l = [nw.route_dirs[r][nw.route_links[r].index(l)]
                               for r in tr.train_routes[s] if r in routes_over_l]
                assert len(set(dirs_over_l)) <= 1, \
                    "This model cannot handle multiple link directions per train - as for %s" % s
                if len(dirs_over_l) > 0:
                    train_dirs_over_l[s] = dirs_over_l[0]
            tr_dirs[l] = train_dirs_over_l
        return TrainSets(tr_periods, tr_links, tr_dirs)
