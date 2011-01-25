#!/bin/sh
# you will need to read the top level README, and run boostrap.py
# and buildout in order to make pyjsbuild

options="$@"
./pyjamas-0.7/bin/pyjsbuild --print-statements $options SketchSystem
