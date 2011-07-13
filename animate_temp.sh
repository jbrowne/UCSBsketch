#!/bin/bash

#ffmpeg -f image2 -i ./temp/%06d.jpg -vcodec flashsv vid.flv

convert -delay 50 -loop 0 temp/*.jpg animation.gif
