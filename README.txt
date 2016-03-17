Readme file for mwo-data

Introduction
============

This repository contains data files and solutions to the maintenance window
optimization problem. The data files are in json format and there are also
a set of python files for loading (parsing) and dumping the files into/from
data classes. In addition there is a plotter module that plots a given solution.

The optimization problem and one possible model for solving it is described
in the paper
* Lidén, T, Joborn, M. Integrated planning of railway traffic and network
maintenance. Transportation Research, part C, Elsevier, submitted April 2016
to Special Issue of Integrated optimization models and algorithms in rail
planning and control.

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

The class TrainSets (in train_sets.py) holds some derived data sets that
makes life easier when working with the problem (used in the plotter for example).

The scheduling solutions are given as
	<name>_sol<id>.json
which correspond to the class
	Solution in solution.py

Note that Solution contains some statistics information about problem size,
objective value, IP gap etc. The solution files are named with and
<id> which should be
	"opt" for a proven a optimal solution and
	"best" for the best known solution so far
	
The module persist.py contains utility functions and some base classes
for handling the json files, loading and dumping.

Usage
=====

You might want to move the python files to some suitable place, perhaps
as a python library or to where your other code is. Feel free to extend or
correct as you like - but try to keep the data files in sync with the
code. Especially, this is important if you want to share your results and
tests with others.

The following python code shows one possible way to read and plot a solution.

--- read_and_plot.py ---
#!/usr/bin/env python

from network import Network
from traffic import Traffic
from maintenance import Maintenance
from train_sets import TrainSets
from solution import Solution
from persist import json_dump, json_load, register
import plotter


--- EOF ---

Disclaimer
==========

This is all made public so as to make it possible for collaboration and
further developments regarding this type of problems. There are no
guarantees. Use it as you like. Suggestions and improvements are most
welcome!

/Tomas Lidén (tomas dot liden at liu dot se)

