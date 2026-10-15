#!/bin/bash

#export BUN_TMPDIR="./tmp"
#export TMPDIR="./tmp"
export EDITOR="vim"
export PATH="~/data/opencode/bin/:$PATH"

ulimit -v 32000000
opencode $1
