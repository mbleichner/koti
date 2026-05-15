#!/bin/sh

steamcmd +@sSteamCmdForcePlatformType linux +login anonymous +app_update 1690800 validate +quit
cd "/home/ubuntu/.local/share/Steam/steamapps/common/SatisfactoryDedicatedServer"
exec ./FactoryServer.sh \
  -log \
  -Port=7777 \
  -ReliablePort=8888 \
  -ServerQueryPort=15777 \
  -BeaconPort=15000 \
  -unattended \
  -multihome=0.0.0.0