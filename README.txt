Readme file for mwo-data

Changelog
---------
2017-09-13: Changed to a more compact storing format for the solutions. Also
updated all result files according to results produced with an improved model,
presented in paper [2] (including four new cases N6-9). In this model the u variables
are explicitly included and xy/xx are binary entry/exit detection variables (instead
of the cumulative approach that was used in [1]).
Finally, the code files have been cleaned up (removed all instance generation stuff).

Introduction
============

This repository contains data files and solutions to the maintenance window
optimization problem. The data files are in json format and there are also
a set of python files for loading (parsing) and dumping the files into/from
data classes. In addition there is a plotter module that plots a given solution.

The optimization problem and one possible model for solving it is described
in the paper
[1] Lidén, T, Joborn, M. Integrated planning of railway traffic and network
maintenance. Transportation Research, part C, Elsevier, 2017.
DOI: 10.1016/j.trc.2016.11.016

An improved model which also include resource considerations is presented in
[2] Lidén, T, Waterer, H, Kalinowski, T. Resource considerations for integrated
planning of railway traffic and maintenance windows. Journal of Rail Transport
Planning and Management, Elsevier, submitted 2017.
(a version of this paper has been presented at RailLille 2017)

All the data files are located in the directory ./cases
All the python files are located in the directory ./code

File descriptions
=================

The data sets are given as three files
	<name>_nw.json     - the railway network
	<name>_tr.json     - the traffic to be scheduled
	<name>_ma.json     - the maintenance to be scheduled
These directly correspond to the the classes
	Network in network.py
	Traffic in traffic.py
	Maintenance in maintenance.py

The scheduling solutions are given as
	<name>_sol<id>.json
which correspond to the class
	Solution in solution.py

Note that Solution contains some statistics information about problem size,
objective value, IP gap etc. The solution files are named with an <id>,
which should be
	"opt" for a proven a optimal solution and
	"best" for the best known solution so far

The class TrainSets (in train_sets.py) holds some derived data sets that
makes life easier when working with the problem (used in plotter for example).

The module persist.py contains utility functions and some base classes
for handling the json files, loading and dumping.

Usage
=====

You might want to move the python files to some suitable place, perhaps
as a python library or to where your other code is. Feel free to extend or
correct as you like - but try to keep the data files in sync with the
code. This is especially important if you want to share your results and
tests with others.

The following python code shows one possible way to read and plot a solution.

--- read_and_plot.py ---
#!/usr/bin/env python

from network import Network
from traffic import Traffic
from maintenance import Maintenance
from train_sets import TrainSets
from solution import Solution
from persist import json_load, register
import plotter

if __name__ == '__main__':
	name = sys.argv[1]
	sol = sys.argv[2]
	# prepare for parsing the json files
	register([Network, Traffic, Maintenance, Solution])
	# read the data files
	with open(name + "_nw.json", "r") as fp:
        nw = json_load(fp)
    with open(name + "_tr.json", "r") as fp:
        tr = json_load(fp)
    with open(name + "_ma.json", "r") as fp:
        ma = json_load(fp)
    # and the solution
    with open(name + "_sol" + sol + ".json", "r") as fp:
        sol = json_load(fp)
    # set up the TrainSets
    train_win = sol.opt_par["train_win"] if "train_win" in sol.opt_par else tr.period_starts[-1]
    ts = TrainSets.setup(nw, tr, train_win)
    # and plot..
    plotter.plot(nw, tr, ts, ma, sol)

--- EOF ---

Disclaimer
==========

This is all made public so as to make it possible for collaboration and
further developments regarding this type of problems. There are no
guarantees. Use it as you like. Suggestions and improvements are most
welcome!

/Tomas Lidén (tomas dot liden at liu dot se)

