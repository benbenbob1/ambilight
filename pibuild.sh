#!/bin/bash
if [ "$1" = "-h" ] || [ "$1" = "--help" ]
then
    echo "Usage: pibuild.sh [SINGLE OPTION]"
    echo "  -h --help : Shows this help message"
    echo "  -ng : Use current file, instead of git pull"
    exit
elif [ "$1" = "-ng" ]
then
    echo "Ignoring git changes"
else
    git checkout .
    git pull
fi

echo "Building rpcVideo for Raspberry Pi..."
g++ $(pkg-config --cflags --libs opencv) -lraspicam -lraspicam_cv videoRPC.cpp -o rpcVideo
