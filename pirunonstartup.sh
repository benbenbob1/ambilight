#!/bin/sh

DIR="/home/pi/ambilight"

sh $DIR/pibuild.sh
ln $DIR/rpcVideo /usr/bin/rpcBuildAndRun
sudo sh /usr/bin/rpcBuildAndRun
