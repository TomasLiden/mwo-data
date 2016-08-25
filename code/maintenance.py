"""
Network maintenance data and accompanying methods
"""
from numbers import Number
from persist import Serializable, Multidict
from random import sample, normalvariate
from math import ceil, pi
import numpy as np

__author__ = 'tomas.liden@liu.se'


class Maintenance(Serializable):
    """
    The maintenance data include work volumes, window options and reduced capacities per link
    together with work and setup costsper link and time.
    Shift counts and lengths are given for each window option.
    """

    def __init__(self, volume, shift_counts, shift_lengths, link_options, red_cap, y_cost, v_cost, num_periods):
        Serializable.__init__(self)
        # @formatter:off
        self.work_volume = volume           # req. work vol. per link   - V_l
        self.shift_counts = shift_counts    # number of shifts per opt  - chi_o
        self.shift_lengths = shift_lengths  # shift length per opt      - nu_o
        self.link_options = link_options    # window options per link   - W_l
        self.red_cap = red_cap      # reduced traffic capacity per link - C^r_l
        self.y_cost = y_cost        # work cost per link and time       - \lambda^t_{lt}
        self.v_cost = v_cost        # setup cost per link, option & t   - \lambda^w_{lot}
        # @formatter:on
        self.__num_periods = num_periods  # help variable for more compact storing/retrieving of data

    def scale(self, y_fac, v_fac):
        return Maintenance(self.work_volume, self.shift_counts, self.shift_lengths,
                           self.link_options, self.red_cap,
                           {k: y_fac*v for k, v in self.y_cost.items()},
                           {k: v_fac*v for k, v in self.v_cost.items()},
                           self.__num_periods)

    @staticmethod
    def from_workdata(window_data, work_data, periods, network, time_variation=None):
        """
        Setting up the data structures
        :param window_data: dictionary with option id as key and tuple(shift_count, shift_length) as value
        :param work_data: dictionary with link as key and work data given as
        1) volume (total time length) with work time cost,
        2) window options with setup cost, and
        3) reduced capacity (per direction and per link)
        If the costs are given as single values, they will be multiplied by time_variation to yield the time variation
        NB: Work data might be given for a subset of the links (with capacity)
        :param periods: a range of period indices
        :param time_variation: the multiplication factors (for y_ and v_cost) to get time variation.
        If None, the factors will be set to 1.
        :param network (class Network): the rail network for which to run the traffic
        """
        work_volume = {}
        shift_counts = {}
        shift_lengths = {}
        link_options = {}
        red_cap = {}
        y_cost = {}
        v_cost = {}
        for o in window_data:
            shift_counts[o], shift_lengths[o] = window_data[o]
        if time_variation is None:
            time_variation = [1] * len(periods)
        assert len(time_variation) == len(periods), "Periods and time_variation not consistent"
        for l in work_data:
            assert l in network.links, "Work data given for a non-existing link: %s" % l
            assert l in network.capacity, "Normal capacity not given for link: %s" % l
            (work_volume[l], yc), opt_data, red_cap[l] = work_data[l]
            Maintenance.__cost_ok(yc, periods, "Work", l)
            for t in periods:
                y_cost[l, t] = yc * time_variation[t] if isinstance(yc, Number) else yc[t]
            link_options[l] = tuple(opt_data.keys())
            for o in opt_data:
                assert o in window_data, "Unknown window option %s given for link %s" % (o, l)
                Maintenance.__cost_ok(opt_data[o], periods, "Setup", l)
                for t in periods:
                    v_cost[l, o, t] = opt_data[o] * time_variation[t] \
                        if isinstance(opt_data[o], Number) else opt_data[o][t]
            assert red_cap[l][0] <= network.capacity[l][0] and red_cap[l][1] <= network.capacity[l][1], \
                "Inconsistent normal (%s) and reduced (%s) capacity for link %s" % \
                (network.capacity[l], red_cap[l], l)
        return Maintenance(work_volume, shift_counts, shift_lengths, link_options, red_cap,
                           y_cost, v_cost, len(periods))

    @staticmethod
    def __cost_ok(c, periods, desc, link):
        assert isinstance(c, Number) or len(c) == len(periods), \
            "%s cost (%s) for link %s not correctly given" % (desc, c, link)

    @staticmethod
    def generate(nw, tr, dat):
        if not nw or not tr or not dat:
            return None
        args = dat.split(':')
        l_share = float(args[0])
        work_med = float(args[1])
        work_dev = float(args[2])
        w_len = [int(v) for v in args[3].split(',')]
        setup = [float(v) for v in args[4].split(',')]
        cost_var = [1] * len(tr.periods)
        if len(args) > 5:
            p2 = float(args[5])
            step = 2 * pi / min(24, len(tr.periods))
            i = np.arange(0, len(tr.periods) * step, step)
            cost_var = (1.0 + p2 * np.cos(i))
        assert len(w_len) == len(setup), 'List of shift lengths does not have the same size as list of setup costs'
        work_volume = {}
        shift_counts = {}
        shift_lengths = {}
        link_options = {}
        red_cap = {}
        y_cost = {}
        v_cost = {}
        for l in sample(nw.links, int(len(nw.links) * l_share)):
            link_options[l] = []
            vol = normalvariate(work_med, work_dev)
            assert vol >= 0, 'Work volume should be >= 0 - probably too large p1 value..'
            work_volume[l] = vol
            for i, wl in enumerate(w_len):
                if i == 0 or vol > w_len[i - 1]:
                    count = int(ceil(vol / wl))
                    k = str(count) + 'x' + str(wl)
                    if k not in shift_counts:
                        shift_counts[k] = count
                        shift_lengths[k] = wl
                    link_options[l].append(k)
                    for t in tr.periods:
                        v_cost[l, k, t] = setup[i] * cost_var[t]
            link_options[l] = tuple(link_options[l])
            track_cap, link_cap = nw.capacity[l]
            if link_cap < 2 * track_cap:
                # single track
                red_cap[l] = (0, 0)
            else:
                red_cap[l] = (track_cap, 1.5 * track_cap)
            for t in tr.periods:
                y_cost[l, t] = 0.1 * cost_var[t]
        return Maintenance(work_volume, shift_counts, shift_lengths, link_options, red_cap,
                           y_cost, v_cost, len(tr.periods))

    @staticmethod
    def __pack(lst):
        return lst[0] if all(x == lst[0] for x in lst) else lst

    def train_passage_possible(self, l):
        return l in self.red_cap and self.red_cap[l][0] > 0

    def __str__(self):
        return "\n".join([
            "Shift counts : %s" % str(self.shift_counts),
            "Shift lengths: %s" % str(self.shift_lengths),
            "Work volume  : %s" % str(self.work_volume),
            "Link options : %s" % str(self.link_options),
            "Reduced cap. : %s" % str(self.red_cap),
            "Work cost    : %s" % str(self.y_cost),
            "Setup cost   : %s" % str(self.v_cost)
        ])

    def to_json(self):
        packed_y_cost = {}
        packed_v_cost = {}
        periods = range(self.__num_periods)
        for l in self.work_volume:
            packed_y_cost[l] = self.__pack([self.y_cost[l, t] for t in periods])
            for o in self.link_options[l]:
                packed_v_cost[l, o] = self.__pack([self.v_cost[l, o, t] for t in periods])
        return self.rep({
            "work_volume": Multidict(self.work_volume),
            "shift_counts": self.shift_counts,
            "shift_lengths": self.shift_lengths,
            "link_options": Multidict(self.link_options),
            "red_cap": Multidict(self.red_cap),
            "y_cost": Multidict(packed_y_cost),
            "v_cost": Multidict(packed_v_cost),
            "num_periods": self.__num_periods
        })

    @staticmethod
    def from_json(chunk):
        num_periods = chunk["num_periods"]
        periods = range(num_periods)
        work_volume = chunk["work_volume"].data
        link_options = {k: tuple(v) for k, v in chunk["link_options"].data.items()}
        packed_y_cost = chunk["y_cost"].data
        packed_v_cost = chunk["v_cost"].data
        # expanding y_cost and v_cost from the packed format
        y_cost = {}
        v_cost = {}
        for l in work_volume:
            yc = packed_y_cost[l]
            for t in periods:
                y_cost[l, t] = yc if isinstance(yc, Number) else yc[t]
            for o in link_options[l]:
                vc = packed_v_cost[l, o]
                for t in periods:
                    v_cost[l, o, t] = vc if isinstance(vc, Number) else vc[t]
        return Maintenance(
            work_volume,
            chunk["shift_counts"],
            chunk["shift_lengths"],
            link_options,
            {k: tuple(v) for k, v in chunk["red_cap"].data.items()},
            y_cost,
            v_cost,
            num_periods
        )
