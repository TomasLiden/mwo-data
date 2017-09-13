"""
A solution to the maintenance window optimization problem
"""
import datetime
import os
from persist import Serializable, Multidict, SparseList

__author__ = 'tomas.liden@liu.se'


# noinspection PyPep8Naming
class TrainSolution(Serializable):
    def __init__(self, z, ey, ex, eO, eD, f, xy, xx, u, n0, n1):
        Serializable.__init__(self)
        self.z = z
        self.ey = ey
        self.ex = ex
        self.eO = eO
        self.eD = eD
        self.f = f
        self.xy = xy
        self.xx = xx
        self.u = u
        self.n0 = n0
        self.n1 = n1

    def __str__(self):
        return "\n".join([
            "TrainSolution",
            "- z     : %s" % str(self.z),
            "- ey    : %s" % str(self.ey),
            "- ex    : %s" % str(self.ex),
            "- eO    : %s" % str(self.eO),
            "- eD    : %s" % str(self.eD),
            "- f     : %s" % str(self.f),
            "- xy    : %s" % str(self.xy),
            "- xx    : %s" % str(self.xx),
            "- u     : %s" % str(self.u),
            "- n0    : %s" % str(self.n0),
            "- n1    : %s" % str(self.n1)
        ])

    def to_json(self):
        packed = {}
        for k in self.ey.keys():
            packed[k] = (self.ey[k],
                         self.ex[k],
                         SparseList.floats(self.u[k]),
                         SparseList.floats(self.xy[k]),
                         SparseList.floats(self.xx[k]))
        return self.rep({
            "z": Multidict(self.z),
            "eO": self.eO,
            "eD": self.eD,
            "f": self.f,
            "n0": Multidict(self.n0),
            "n1": Multidict(self.n1),
            "e_u_x": Multidict(packed)
        })

    @staticmethod
    def from_json(chunk):
        ey = {}
        ex = {}
        u = {}
        xy = {}
        xx = {}
        if "e_u_x" in chunk:
            for k in chunk["e_u_x"].data.keys():
                v = chunk["e_u_x"].data[k]
                ey[k], ex[k] = v[0], v[1]
                u[k], xy[k], xx[k] = v[2].as_list(), v[3].as_list(), v[4].as_list()
        else:
            ey = chunk["ey"].data
            ex = chunk["ex"].data
            u = chunk["u"].data
            xy = chunk["xy"].data
            xx = chunk["xx"].data
        return TrainSolution(
            chunk["z"].data,
            ey,
            ex,
            chunk["eO"],
            chunk["eD"],
            chunk["f"],
            xy,
            xx,
            u,
            chunk["n0"].data,
            chunk["n1"].data
        )


class MaintSolution(Serializable):
    def __init__(self, w, y, v):
        Serializable.__init__(self)
        self.w = w
        self.y = y
        self.v = v

    def __str__(self):
        return "\n".join([
            "MaintSolution",
            "- w     : %s" % str(self.w),
            "- y     : %s" % str(self.y),
            "- v     : %s" % str(self.v)
        ])

    def to_json(self):
        return self.rep({
            "w": Multidict(self.w),
            "y": Multidict(self.y),
            "v": Multidict(self.v)
        })

    @staticmethod
    def from_json(chunk):
        return MaintSolution(
            chunk["w"].data,
            chunk["y"].data,
            chunk["v"].data
        )


class CrewSolution(Serializable):
    def __init__(self, q, yk, vk, d):
        Serializable.__init__(self)
        self.q = q
        self.yk = yk
        self.vk = vk
        self.d = d

    def __str__(self):
        return "\n".join([
            "CrewSolution",
            "- q     : %s" % str(self.q),
            "- yk    : %s" % str(self.yk),
            "- vk    : %s" % str(self.vk),
            "- d     : %s" % str(self.d),
        ])

    def to_json(self):
        return self.rep({
            "q": self.q,
            "yk": self.yk,
            "vk": self.vk,
            "d": Multidict(self.d)
        })

    @staticmethod
    def from_json(chunk):
        return CrewSolution(
            chunk["q"],
            chunk["yk"],
            chunk["vk"],
            chunk["d"].data
        )


class Solution(Serializable):
    def __init__(self, prob, train_sol, maint_sol, crew_sol, opt_par, stat):
        Serializable.__init__(self)
        self.prob = prob
        self.train_sol = train_sol
        self.maint_sol = maint_sol
        self.crew_sol = crew_sol
        self.opt_par = opt_par
        self.stat = stat

    def obj_val(self):
        return self.stat["obj_val"]

    def obj_bnd(self):
        return self.stat["obj_bnd"]

    def gap(self):
        return self.stat["gap"]

    def num_cancelled(self):
        return self.stat["num_cnl"]

    def num_var(self):
        return self.stat["num_var"]

    def num_ctr(self):
        return self.stat["num_ctr"]

    def nodes(self):
        return self.stat["nodes"]

    def iter(self):
        return self.stat["iter"]

    def time(self):
        return self.stat["time"]

    def linear(self):
        return "linear" in self.stat and self.stat["linear"]

    def info(self):
        print
        print "Objective value:", self.obj_val()
        print "Best bound     :", self.obj_bnd()
        print
        print 'Num cancelled trains:', self.num_cancelled()
        print
        print "Problem statistics"
        print "- variables  :", self.num_var()
        print "- constraints:", self.num_ctr()
        print "- nodes      :", self.nodes()
        print "- iterations :", self.iter()
        print "- time [s]   :", self.time()

    def write_statistics(self, filename):
        with open(filename, "a") as fp:
            # Output #var, #constr, obj-val, best-bound, gap, nodes, iters, time
            time_str = str(datetime.timedelta(seconds=int(self.time())))
            line = "\t%s,%s,%.2f,%.2f,%.2f%%,%s,%s,%s,%s" %\
                   (self.num_var(), self.num_ctr(),
                    self.obj_val(), self.obj_bnd(), self.gap(), self.num_cancelled(),
                    self.nodes(), self.iter(), time_str)
            fp.write(line + os.linesep)

    def __str__(self):
        return "\n".join([
            "Problem : %s" % self.prob,
            "- params: %s" % str(self. opt_par),
            "- stat  : %s" % str(self.stat),
            str(self.train_sol),
            str(self.maint_sol),
            str(self.crew_sol)
        ])

    def to_json(self):
        return self.rep({
            "prob": self.prob,
            "opt_par": self.opt_par,
            "stat": self.stat,
            "train_sol": self.train_sol,
            "maint_sol": self.maint_sol,
            "crew_sol": self.crew_sol
        })

    # noinspection PyPep8Naming
    @staticmethod
    def from_json(chunk):
        old_format = "z" in chunk
        if old_format:
            z, ey, ex, eO, eD, f, xy, xx, n0, n1 = (
                chunk["z"].data,
                chunk["ey"].data, chunk["ex"].data,
                chunk["eO"], chunk["eD"], chunk["f"],
                chunk["xy"].data, chunk["xx"].data,
                chunk["n0"].data, chunk["n1"].data,
            )
            # Was using cumulative variables then, derive u from them
            u = {}
            for key in xx.keys():
                xx0 = [0] + xx[key]
                u_val = [xy[key][t] - xx0[t] for t in range(len(xy[key]))]
                u[key] = u_val
            train_sol = TrainSolution(z, ey, ex, eO, eD, f, xy, xx, u, n0, n1)
            # Unpack maint_sol
            maint_sol = MaintSolution.from_json(chunk)
            crew_sol = None
        else:
            train_sol = chunk["train_sol"]
            maint_sol = chunk["maint_sol"]
            crew_sol = chunk["crew_sol"]

        return Solution(
            chunk["prob"],
            train_sol,
            maint_sol,
            crew_sol,
            chunk["opt_par"],
            chunk["stat"]
        )

# Convenience list for use when registering in Persist
types = [Solution, TrainSolution, MaintSolution, CrewSolution]
