"""
Graphical plotting of the network and results - using matplotlib
"""
import matplotlib.pyplot as plt
from matplotlib import gridspec
from math import sqrt

__author__ = 'tomas.liden@liu.se'


links = {}
plot_links = []
trains = {}


def line_picker(event):
    line = event.artist
    if line in links:
        link = links[line]
        if link in plot_links:
            idx = plot_links.index(link)
            plot_links.pop(idx)
            plot_dirs.pop(idx)
            # print "Removed", link, "->", plot_links, plot_dirs
            line.set_color('grey')
        else:
            last_node = plot_links[-1][plot_dirs[-1]] if len(plot_links) else None
            plot_links.append(link)
            if last_node == link[1]:
                plot_dirs.append(0)
            else:
                d = 1 if event.mouseevent.button == 1 else 0
                plot_dirs.append(d)
            # print "Added", link, "->", plot_links, plot_dirs
            line.set_color('blue')
        td_graph.cla()
        plot_traingraph(td_graph)
    if line in trains:
        s = trains[line]
        col = 'green' if line.get_color() == 'red' else 'red'
        if col == 'red':
            me = event.mouseevent
            td_graph.annotate(s, xy=(me.xdata, me.ydata), xycoords='data', xytext=(5, -2), textcoords='offset points')
        for l in trains:
            if trains[l] == s:
                l.set_color(col)
    event.canvas.draw()


double_track_links = []
work_links = []
plot_dirs = []


def plot(title, nw, tr, ts, ma, rs, sol):
    """
    Creating a basic network plot
    :param title: the text to show as window title
    :param nw: the network data (class Network)
    :param tr: the traffic data (class Traffic)
    :param ts: the additional train sets (class TrainSets)
    :param ma: the maintenance data (class Maintenance)
    :param rs: the resource data (class Resources)
    :param sol: a planning solution (class Solution)
    :return: the figure (class Figure)
    """
    global plot_links, double_track_links, work_links, plot_dirs
    r = max(nw.routes.items(), key=lambda kv: len(kv[1]))[0]
    plot_links = list(nw.route_links[r])
    double_track_links = [l for l in nw.links if not nw.single_track(l)]
    work_links = list(ma.work_volume.keys())
    plot_dirs = list(nw.route_dirs[r])

    # noinspection PyGlobalUndefined
    global td_graph, nw_graph, traffic, train_dirs, solution, bases, crew
    fig = plt.figure(figsize=(12, 8))
    fig.canvas.set_window_title(title)
    gs = gridspec.GridSpec(2, 1, height_ratios=(2, 1))
    td_graph = plt.subplot(gs[0])
    nw_graph = plt.subplot(gs[1])
    plot_network(nw, nw_graph)
    fig.canvas.mpl_connect('pick_event', line_picker)
    traffic = tr
    train_dirs = ts.dirs_over
    solution = sol
    if rs:
        bases = rs.bases
        crew = rs.all_crew
    plot_traingraph(td_graph)
    plt.show(block=True)  # stop here until done

# Node coordinates
x_n = {}
y_n = {}


def length(l):
    fr, to = l
    return sqrt((x_n[fr] - x_n[to])**2 + (y_n[fr] - y_n[to])**2)


def plot_network(nw, ax):
    ax.set_title('Network')
    ax.set_xticklabels([], visible=False)
    ax.set_xticks([])
    ax.set_yticklabels([], visible=False)
    ax.set_yticks([])
    ax.margins(0.05, 0.15)
    x, y = zip(*nw.nodes.values())
    ax.scatter(x, y, zorder=2)
    for i, n in enumerate(nw.nodes.keys()):
        x_n[n] = x[i]
        y_n[n] = y[i]
        ax.annotate(n, (x_n[n], y_n[n]), xytext=(-4, 5), textcoords='offset points')
    for link in nw.links:
        fr = link[0]
        to = link[1]
        col = 'blue' if link in plot_links else 'grey'
        line, = ax.plot([x_n[fr], x_n[to]], [y_n[fr], y_n[to]], col, picker=5, zorder=1)
        if link in double_track_links:
            line.set_linewidth(3)
            ax.plot([x_n[fr], x_n[to]], [y_n[fr], y_n[to]], 'white', zorder=1)
        links[line] = link


def plot_traingraph(ax):
    if not traffic or not solution:
        return
    nodes = []
    ticks = []
    z = 0.0
    z_l = {}
    # plot the y axis with station markers and horizontal bars between line sequences
    for i, l in enumerate(plot_links):
        fr = l[1 - plot_dirs[i]]
        to = l[plot_dirs[i]]
        dz = length(l)
        if len(nodes) == 0 or fr != nodes[-1]:
            if len(nodes) > 0:
                ax.axhspan(z, z + 0.1, fc='grey', alpha=0.5)
                z += 0.1
            nodes.append(fr)
            ticks.append(z)
        else:
            ax.axhline(z, c='k', ls=':')
        z_l[l] = [z, z + dz]
        nodes.append(to)
        ticks.append(z + dz)
        z += dz
    ax.set_title('Train and work graph')
    ax.set_yticks(ticks)
    ax.set_yticklabels(nodes)
    # shortest link length
    min_len = min(z_l[l][1] - z_l[l][0] for l in plot_links)
    # plot the solution data
    tr_sol = solution.train_sol
    ma_sol = solution.maint_sol
    cr_sol = solution.crew_sol
    for i, l in enumerate(plot_links):
        # plot trains running over l
        for s in train_dirs[l]:
            if (s, l) in tr_sol.ey:
                x = [tr_sol.ey[s, l], tr_sol.ex[s, l]]
                y = z_l[l]
                if train_dirs[l][s] != plot_dirs[i]:
                    y = z_l[l][::-1]
                line, = ax.plot(x, y, 'green', picker=5)
                trains[line] = s
        # plot work windows
        tr = traffic
        if l in work_links:
            x = []
            c = []
            for t in tr.periods:
                value = ma_sol.y[l][t] if l in ma_sol.y else 0.0
                if value > 0.01:
                    x.append((tr.period_starts[t], tr.period_lengths[t]))
                    c.append((1, 1, 1 - value))  # level of yellow show sol-value
                    if value < 1.0:
                        px = tr.period_starts[t] + 0.5 * tr.period_lengths[t]
                        py = z_l[l][0] + 0.5 * length(l)
                        ax.annotate(format(value, ".2f"), (px, py))
            ax.broken_barh(x, (z_l[l][0], length(l)), facecolors=c, linewidth=0.0)
            # plot the crew assignments
            if cr_sol:
                crew_colors = ['red', 'blue', 'black', 'orange', 'green', 'gray', 'cyan', 'pink', 'brown', 'magenta']
                # Other color maps: seismic, flag, gnuplot2, gnuplot, terrain
                for ki, k in enumerate(crew):
                    x = []
                    y = (z_l[l][0] + 0.25 * min_len, 0.35 * min_len)
                    col = crew_colors[ki % len(crew_colors)]
                    if (l, k) in cr_sol.d:
                        for t in tr.periods:
                            if cr_sol.d[l, k][t] > 0.1:
                                x.append((tr.period_starts[t], tr.period_lengths[t]))
                    if len(x):
                        hatching = '|||' if cr_sol.q[k] < 0.1 else None
                        ax.broken_barh(x, y, facecolor=col, linewidth=0.0, edgecolor='white', hatch=hatching)
    # plot double track markers
    for i, l in enumerate(plot_links):
        if l in double_track_links:
            y = [z_l[l][0] / z, z_l[l][1] / z]
            # This transform fixes both x and y - but ideally we would like y to follow the data
            # in order to adjust to manual zoom & pan
            ax.plot([-0.004, -0.004], y, 'black', clip_on=False, transform=ax.transAxes)
            ax.plot([1.004, 1.004], y, 'black', clip_on=False, transform=ax.transAxes)
