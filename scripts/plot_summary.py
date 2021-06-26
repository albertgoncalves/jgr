#!/usr/bin/env python3

from math import ceil
from sys import argv

from matplotlib.pyplot import close, savefig, subplots, tight_layout
from numpy import mean, median
from pandas import read_csv


def plot(ax, samples, column):
    ax.set_title(column)
    ax.plot(samples[column], color="black", alpha=0.35)
    kwargs = {
        "ls": "--",
    }
    x = median(samples[column])
    ax.axhline(x, label=f"median => {x:.2f}", c="dodgerblue", **kwargs)
    x = mean(samples[column])
    ax.axhline(x, label=f"mean   => {x:.2f}", c="tomato", **kwargs)
    ax.legend(loc="lower right", prop={"family": "monospace"})


def main():
    assert len(argv) == 4
    samples = read_csv(argv[2], low_memory=False)
    n = min(30, len(samples.columns))
    w = int(argv[1])
    h = ceil(n / w)
    (_, axs) = subplots(h, w, figsize=(28, 15), dpi=65)
    for i in range(h):
        iw = i * w
        for j in range(w):
            m = iw + j
            if m < n:
                plot(axs[i, j], samples, samples.columns[m])
            else:
                axs[i, j].set_axis_off()
    tight_layout()
    savefig(argv[3])
    close()


if __name__ == "__main__":
    main()
