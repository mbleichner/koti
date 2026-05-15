#!/bin/sh

steamcmd +@sSteamCmdForcePlatformType windows +login anonymous +app_update 2857200 validate +quit
cd "/home/ubuntu/.local/share/Steam/steamapps/common/Abiotic Factor Dedicated Server/AbioticFactor/Binaries/Win64"
exec wine AbioticFactorServer-Win64-Shipping.exe \
  -PORT=7777 \
  -QueryPort=27015 \
  -useperfthreads \
  -NoAsyncLoadingThread \
  -MaxServerPlayers=16 \
  -ServerPassword="$ServerPassword" \
  -AdminPassword="$AdminPassword" \
  -SteamServerName="Moep" \
  -WorldSaveName="Cascade"