#!/bin/sh

DIR="/home/pi/ambilight"
cd $DIR
echo "Startup up pirunonstartup script" >> /var/log/rpcVideo.log
CDIR=$(pwd); echo "Currently in $CDIR" >> /var/log/rpcVideo.log
if [ -f rpcVideo ]
then
    echo "Running rpcVideo..." >> /var/log/rpcVideo.log
    sudo ./rpcVideo >> /var/log/rpcVideo.log
else
    echo "rpvVideo not found. Exiting..." >> /var/log/rpcVideo.log
    exit
fi
#sudo ln -f $DIR/rpcVideo /usr/bin/rpcBuildAndRun
#sudo sh /usr/bin/rpcBuildAndRun
