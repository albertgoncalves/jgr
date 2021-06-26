#!/usr/bin/env bash

set -eu

wd="$WD/model"

for x in build out; do
    if [ ! -d "$wd/$x" ]; then
        mkdir "$wd/$x"
    fi
done

(
    "$WD/scripts/install_cmdstan.sh"
    if ! cmp -s "$wd/model.stan" "$wd/build/model.stan"; then
        cp "$wd/model.stan" "$wd/build"
        "$WD/cmdstan/bin/stanc" \
            --warn-uninitialized \
            --warn-pedantic \
            "$wd/build/model.stan"
    fi
)
(
    . "$WD/scripts/build_flags.sh"
    cd "$WD/cmdstan"
    make "$wd/build/model"
)
(
    "$wd/export_data.py"
    "$wd/build/model" \
        sample \
        num_warmup=1000 \
        num_samples=1000 \
        data file="$wd/out/data.json" \
        output file="$wd/out/output.csv"
    grep -v "#" "$wd/out/output.csv" > "$wd/out/samples.csv"
    "$WD/cmdstan/bin/stansummary" "$wd/out/output.csv" \
        > "$wd/out/summary.txt"
    "$WD/scripts/plot_summary.py" 3 "$wd/out/samples.csv" "$wd/out/summary.png"
)
(
    less "$wd/out/summary.txt"
    feh "$wd/out/summary.png"
)
