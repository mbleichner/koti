#!/usr/bin/python3
import sys
import time
import subprocess

freq_baseline = int(sys.argv[1])

freq_by_process = {

  # games and steam processes
  "SteamLinuxRuntime": 4000,  # ... usually means some steam game is running
  "wineserver": 4000,  # .......... usually means some proton game is running
  "fossilize": 3000,  # ........... speed up the fossilize processes a bit
  "/usr/bin/eden": 3000,  # ....... switch emulator
  "beyond-all-reason": 4000,

  # system updates, compilation, etc
  "koti": 3500,
  "pacman": 3500,
  "makepkg": 3500,
}

while True:
  running_processes = subprocess.check_output(["/usr/bin/ps", "-eo", "args"], shell = False).decode("utf-8")
  max_speed = freq_baseline
  for proc, speed in freq_by_process.items():
    if speed > max_speed and proc in running_processes:
      max_speed = speed
  subprocess.check_output(f"/opt/systray/cpu/actions/max-freq-{max_speed}mhz")
  time.sleep(3)
