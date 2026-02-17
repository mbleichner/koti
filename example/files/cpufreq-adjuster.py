#!/usr/bin/python3
import os
import sys
import time
import subprocess

import yaml

os.nice(19)

# load state
try:
  with open("/etc/cpufreq/state.yaml", "r") as stream:
    saved_state = yaml.safe_load(stream) or {}
except FileNotFoundError:
  saved_state = {}

# merge with defaults
default_state = {"mode": sys.argv[1], "freq": int(sys.argv[2])}
state = {**default_state, **saved_state}

# update yaml file if effective state differs
if saved_state != state:
  with open("/etc/cpufreq/state.yaml", "w") as stream:
    yaml.dump(state, stream)

print(state)

mode = state["mode"]
assert mode in ["manual", "auto"]
if mode == "auto":

  with open("/etc/cpufreq/rules.yaml") as stream:
    freq_by_process = yaml.safe_load(stream)
    print(freq_by_process)

  hide_kernel_threads = {"LIBPROC_HIDE_KERNEL": "1"}
  while True:
    running_processes = {
      *subprocess.check_output(["/usr/bin/ps", "--no-headers", "-eo", "exe"], shell = False, env = hide_kernel_threads).decode("utf-8").splitlines(),
      *subprocess.check_output(["/usr/bin/ps", "--no-headers", "-eo", "args"], shell = False, env = hide_kernel_threads).decode("utf-8").splitlines()
    }
    #print(running_processes)
    new_freq = int(state["freq"])
    for expr, speed in freq_by_process.items():
      if speed > new_freq and any(expr in proc for proc in running_processes):
        new_freq = speed
    print(new_freq)
    subprocess.check_output(["/usr/bin/cpupower", "frequency-set", "-u", f"{new_freq}MHz"])
    time.sleep(5)

if mode == "manual":
  new_freq = int(state["freq"])
  print(f"setting cpu max freq to {new_freq}")
  subprocess.check_output(["/usr/bin/cpupower", "frequency-set", "-u", f"{new_freq}MHz"])
