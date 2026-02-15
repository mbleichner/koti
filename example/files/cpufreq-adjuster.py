#!/usr/bin/python3
import os
import time
import subprocess

import yaml

os.nice(19)

with open("/etc/cpufreq/settings.yaml") as stream:
  settings = yaml.safe_load(stream)
  print(settings)

mode = settings["mode"]
assert mode in ["manual", "auto"]

if mode == "auto":

  with open("/etc/cpufreq/rules.yaml") as stream:
    freq_by_process = yaml.safe_load(stream)
    print(freq_by_process)

  while True:
    new_freq = int(settings["freq"])

    running_processes = subprocess.check_output(["/usr/bin/ps", "-eo", "args"], shell = False).decode("utf-8")
    for proc, speed in freq_by_process.items():
      if speed > new_freq and proc in running_processes:
        new_freq = speed
    subprocess.check_output(["/usr/bin/cpupower", "frequency-set", "-u", f"{new_freq}MHz"])

    time.sleep(5)

if mode == "manual":
  new_freq = int(settings["freq"])
  print(f"setting cpu max freq to {new_freq}")
  subprocess.check_output(["/usr/bin/cpupower", "frequency-set", "-u", f"{new_freq}MHz"])
