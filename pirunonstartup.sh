#!/bin/sh

DIR="/home/pi/ambilight"

sh $DIR/pibuild.sh
sudo $DIR/rpcVideo
#sudo ln -f $DIR/rpcVideo /usr/bin/rpcBuildAndRun
#sudo sh /usr/bin/rpcBuildAndRun
