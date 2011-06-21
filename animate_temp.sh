#!/bin/bash

ffmpeg -f image2 -i ./temp/%06d.jpg vid.mpg
#convert -delay 4 -loop 0 temp/*.jpg animation.gif
