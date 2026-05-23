#!/bin/sh

mkdir -p "/home/ubuntu/backups"
cd "/home/ubuntu/.local/share/Steam/steamapps/common/Abiotic Factor Dedicated Server/AbioticFactor/Saved/SaveGames"

BACKUPFILE=$(date '+%Y%m%d-%H%M').tar.gz
echo "creating backup $BACKUPFILE"
tar czf "/home/ubuntu/backups/${BACKUPFILE}" ./
echo "backup created."