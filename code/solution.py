"""
A solution to the maintenance window optimization problem
"""
import datetime
import os
import numpy as np
from persist import Serializable, Multidict

__author__ = 'tomas.liden@liu.se'


class PrettyFloat(float):
    def __repr__(self):
        return "%5.2f" % self if self != 0.0 else "     "


class Solution(Serializable):
    def __init__(self, prob, z, ey, ex, eO, eD, f, xy, xx, n0, n1, w, y, v, opt_par, stat):
        Serializable.__init__(self)
        self.prob = prob
        self.z = z
        self.ey = ey; self.ex = ex
        self.eO = eO; self.eD = eD; self.f = f
        self.xy = xy; self.xx = xx
        self.n0 = n0; self.n1 = n1
        self.w = w; self.y = y; self.v = v
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

    @staticmethod
    def _fmt_list(d):
        return map(PrettyFloat, d)

    def diagnose(self, nw, tr, ts, ma, verbose):
        print "Objective value:", self.obj_val()
        if verbose:
            self._diag_details(nw, tr, ts, ma)
        print
        print 'Num cancelled trains:', self.num_cancelled()
        print
        print "Problem statistics"
        print "- variables  :", self.num_var()
        print "- constraints:", self.num_ctr()
        print "- nodes      :", self.nodes()
        print "- iterations :", self.iter()
        print "- time [s]   :", self.time()

    def _diag_details(self, nw, tr, ts, ma):
        print
        print "Chosen routes / event timing:"
        num_cancelled = 0
        n0_est = {(l, t): 0.0 for l in nw.links for t in tr.periods}
        n1_est = {(l, t): 0.0 for l in nw.links for t in tr.periods}
        for s in tr.trains:
            last_t = ts.periods[s][-1]
            print "%s %.2f - %.2f, %.2f" % (s, self.eO[s], self.eD[s], self.f[s]),
            for r in tr.train_routes[s]:
                if (s, r) in self.z and self.z[s, r] > 0.0:
                    print ":", r,
                    num_cancelled += (len(nw.route_links[r]) == 0)
                    if nw.route_links[r]:
                        x0_ok = sum(self.xy[s, l][last_t] == 1
                                    for l in nw.route_links[r]) == len(nw.route_links[r])
                        x1_ok = sum(self.xx[s, l][last_t] == 1
                                    for l in nw.route_links[r]) == len(nw.route_links[r])
                        chk = ("ok" if x0_ok and x1_ok else "NOT OK!!")
                        print "- link usage check: %s" % chk,
                        dep_ok = abs(self.eO[s] - self.ey[s, nw.route_links[r][0]]) < 0.01
                        arr_ok = abs(self.eD[s] - self.ex[s, nw.route_links[r][-1]]) < 0.01
                        chk = ("ok" if dep_ok and arr_ok else "NOT OK!!")
                        print ", dep/arr check: %s" % chk
                        min_dur = tr.min_dur(s, r, nw.route_nodes[r])
                        e = self.eO[s]
                        for i, l in enumerate(nw.route_links[r]):
                            d = self.eD[s] - min_dur + tr.min_link_time[s, r][i]
                            t_use = [t for t in ts.periods[s]
                                     if e < tr.period_starts[t] + tr.period_lengths[t] - 0.001 and
                                     d > tr.period_starts[t] + 0.001]
                            for t in t_use:
                                if nw.route_dirs[r][i]:
                                    n1_est[l, t] += self.z[s, r]
                                else:
                                    n0_est[l, t] += self.z[s, r]
                            dur = tr.min_link_time[s, r][i]
                            n = l[nw.route_dirs[r][i]]
                            if (s, n) in tr.min_node_time:
                                dur += tr.min_node_time[s, n]
                            e += dur
                            min_dur -= dur
                    print "\t", ["%s: %.2f - %.2f," % (l, self.ey[s, l], self.ex[s, l])
                                 for l in nw.route_links[r]]
        if self.linear() and len(tr.periods) < 24:
            print "Entry/exit"
            invar1_sum = invar2_sum = 0
            for l in nw.links:
                print l
                for s in tr.trains:
                    if l in ts.links[s]:
                        b = " " * len(s)
                        invar1 = invar2 = 0
                        for t in ts.periods[s]:
                            invar1 += self.xx[s, l][t] > (self.xy[s, l][t] + 0.000001)
                            if t < ts.periods[s][-1]:
                                invar2 += self.xx[s, l][t] > (self.xy[s, l][t + 1] + 0.000001)
                        print s, "y:", self._fmt_list(self.xy[s, l])
                        print b, "x:", self._fmt_list(self.xx[s, l]), "invariant errors:", invar1, invar2
                        counts = [self.xy[s, l][ts.periods[s][0]], ] + \
                                 [self.xy[s, l][t] - self.xx[s, l][t - 1] for t in ts.periods[s][1:]]
                        print b, "d:",
                        if ts.periods[s][0] > tr.periods[0]:
                            print " " * (7 + 8 * (ts.periods[s][0] - tr.periods[0] - 1)),
                        print self._fmt_list(counts)
                        invar1_sum += invar1
                        invar2_sum += invar2
            print "Sum of invariant errors:", invar1_sum, invar2_sum
        print "Train counting:"
        print "Link/Time", tr.period_starts, "[error values]",
        print "[mean, std]" if self.linear() else ""
        count_errors = np.empty((2 * len(nw.links), len(tr.periods)))
        np.set_printoptions(2, suppress=True)
        for i, l in enumerate(nw.links):
            print l, "0:", self._fmt_list(self.n0[l]),
            row = count_errors[i * 2, :] = [self.n0[l][t] - n0_est[l, t] for t in tr.periods]
            print count_errors[i * 2, :], np.array([np.mean(row), np.std(row)]) if self.linear() else ""
            print l, "1:", self._fmt_list(self.n1[l]),
            row = count_errors[i * 2 + 1, :] = [self.n1[l][t] - n1_est[l, t] for t in tr.periods]
            print count_errors[i * 2 + 1, :], np.array([np.mean(row), np.std(row)]) if self.linear() else ""
        if self.linear():
            print "\tPeriod mean:", np.mean(count_errors, axis=0), np.mean(count_errors)
            print "\tPeriod std :", np.std(count_errors, axis=0), np.std(count_errors)
        print "Work assignment:"
        for l in ma.work_volume:
            if not self.linear():
                print l, [int(round(self.y[l][t])) for t in tr.periods],
            else:
                print l, self._fmt_list(self.y[l]),
            for o in ma.link_options[l]:
                if (l, o) in self.w and self.w[l, o] > 0.5:
                    print "with work option", o
            fmt_spec = '{:>%s}' % len(str(l))
            for o in ma.link_options[l]:
                if self.linear() and (l, o) in self.w and self.w[l, o] > 0.0:
                    print fmt_spec.format(o), self._fmt_list(self.v[l, o]),
                    print 'w = %.2f' % self.w[l, o]
                for t in tr.periods:
                    work_start = self.y[l][t] > 0.5 and \
                                 (t == 0 or self.y[l][t - 1] < 0.5) and \
                                 (l, o) in self.w and self.w[l, o] > 0.5
                    if not self.linear():
                        assert (self.v[l, o][t] > 0.5) == work_start, "Inconsistent work start " + self.v[l, o][t]

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
            "- z     : %s" % str(self.z),
            "- ey    : %s" % str(self.ey),
            "- ex    : %s" % str(self.ex),
            "- eO    : %s" % str(self.eO),
            "- eD    : %s" % str(self.eD),
            "- f     : %s" % str(self.f),
            "- xy    : %s" % str(self.xy),
            "- xx    : %s" % str(self.xx),
            "- n0    : %s" % str(self.n0),
            "- n1    : %s" % str(self.n1),
            "- w     : %s" % str(self.w),
            "- y     : %s" % str(self.y),
            "- v     : %s" % str(self.v),
            "- params: %s" % str(self. opt_par),
            "- stat  : %s" % str(self.stat)
        ])

    def to_json(self):
        return self.rep({
            "prob": self.prob,
            "z": Multidict(self.z),
            "ey": Multidict(self.ey), "ex": Multidict(self.ex),
            "eO": self.eO, "eD": self.eD, "f": self.f,
            "xy": Multidict(self.xy), "xx": Multidict(self.xx),
            "n0": Multidict(self.n0), "n1": Multidict(self.n1),
            "w": Multidict(self.w), "y": Multidict(self.y), "v": Multidict(self.v),
            "opt_par": self.opt_par,
            "stat": self.stat
        })

    @staticmethod
    def from_json(chunk):
        return Solution(
            chunk["prob"],
            chunk["z"].data,
            chunk["ey"].data, chunk["ex"].data,
            chunk["eO"], chunk["eD"], chunk["f"],
            chunk["xy"].data, chunk["xx"].data,
            chunk["n0"].data, chunk["n1"].data,
            chunk["w"].data, chunk["y"].data, chunk["v"].data,
            chunk["opt_par"],
            chunk["stat"]
        )
