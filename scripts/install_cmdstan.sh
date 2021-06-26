#!/usr/bin/env bash

set -eu

if [ ! -d "$WD/cmdstan" ]; then
    (
        cd "$WD"
        git clone https://github.com/stan-dev/cmdstan.git --recursive
        cd "$WD/cmdstan"
        make build
    )
fi
