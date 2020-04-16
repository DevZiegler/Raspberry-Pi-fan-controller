#!/bin/sh
# launcher.sh

gcc -Wall `pkg-config --cflags gtk+-2.0 lxpanel` -shared -fPIC rpm.c -o rpm.so `pkg-config --libs lxpanel`
sudo cp rpm.so /usr/lib/arm-linux-gnueabihf/lxpanel/plugins/rpm.so
