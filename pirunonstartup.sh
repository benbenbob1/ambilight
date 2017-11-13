#!/bin/sh

DIR="/home/pi/ambilight"

sh $DIR/pibuild.sh
sudo ln -f $DIR/rpcVideo /usr/bin/rpcBuildAndRun
sudo sh /usr/bin/rpcBuildAndRun
