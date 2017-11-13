#!/bin/sh

DIR="/home/pi/ambilight"
cd $DIR
CDIR=$(pwd); echo "Currently in $CDIR"
if [ -f rpcVideo ]
then
    echo "Running..."
    sudo rpcVideo &
else
    echo "rpvVideo not found. Exiting..."
    exit
fi
#sudo ln -f $DIR/rpcVideo /usr/bin/rpcBuildAndRun
#sudo sh /usr/bin/rpcBuildAndRun
