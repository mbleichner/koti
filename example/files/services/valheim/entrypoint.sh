#!/bin/sh

steamcmd +@sSteamCmdForcePlatformType linux +login anonymous +app_update 896660 validate +quit

# from start_server.sh:
cd "/home/ubuntu/.local/share/Steam/steamapps/common/Valheim dedicated server"
export LD_LIBRARY_PATH=./linux64:$LD_LIBRARY_PATH
export SteamAppId=892970
exec ./valheim_server.x86_64 \
  -public 0 \
  -name "Moep" \
  -port 2456 \
  -world "Dedicated" \
  -password "$ServerPassword" \
  -backups 14 \
  -backupshort 1800 \
  -backuplong 43200