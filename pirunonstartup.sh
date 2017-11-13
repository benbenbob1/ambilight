#!/bin/sh

DIR="/home/pi/ambilight"
cd $DIR
CDIR=$(pwd); echo "Currently in $CDIR"
sh pibuild.sh
echo "Running..."
sudo rpcVideo &
#sudo ln -f $DIR/rpcVideo /usr/bin/rpcBuildAndRun
#sudo sh /usr/bin/rpcBuildAndRun
