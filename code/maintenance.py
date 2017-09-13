"""
Network maintenance data and accompanying methods
"""
from numbers import Number
from persist import Serializable, Multidict

__author__ = 'tomas.liden@liu.se'


class Maintenance(Serializable):
    """
    The maintenance data include work volumes, window options and reduced capacities per link
    together with work and setup costs per link and time.
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
    def __pack(lst):
        return lst[0] if all(x == lst[0] for x in lst) else lst

    def train_passage_possible(self, l):
        return l in self.red_cap and self.red_cap[l][0] > 0

    def min_maint_time(self, o, min_dt, cyclic=False):
        wt = self.shift_counts[o] * self.shift_lengths[o]
        if cyclic:
            return wt + (self.shift_counts[o] - 1) * min_dt
        else:
            return wt + max(0, (self.shift_counts[o] - 2) * min_dt)

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
