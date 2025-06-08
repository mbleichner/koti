#!/bin/bash -ex

# Sets up everything that is needed to run koti for my setup (base-devel + paru)
sudo pacman -Syu
sudo pacman -S git base-devel
rm -rf /tmp/paru-bin
git clone https://aur.archlinux.org/paru-bin.git /tmp/paru-bin
cd /tmp/paru-bin
makepkg -si
