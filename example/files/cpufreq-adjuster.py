#!/usr/bin/python3

import sys
import time
import subprocess

import yaml

statefile = "/tmp/cpufreq.state.yaml"
default_state = {"mode": sys.argv[1], "base": int(sys.argv[2])}

with open("/etc/cpufreq/rules.yaml") as stream:
  freq_by_process = yaml.safe_load(stream)
  print(freq_by_process)

hide_kernel_threads = {"LIBPROC_HIDE_KERNEL": "1"}
while True:

  # load state and merge with the defaults provided at startup
  try:
    with open(statefile, "r") as stream:
      saved_state = yaml.safe_load(stream) or {}
  except FileNotFoundError:
    saved_state = {}
  state = {**default_state, **saved_state}

  # update state file if effective state differs
  # (needed for reading the current state in the systray summary script)
  if saved_state != state:
    with open(statefile, "w") as stream:
      yaml.dump(state, stream)

  if state["mode"] == "suspend":
    continue
  elif state["mode"] == "fixed":
    new_freq = int(state["base"])
  elif state["mode"] == "auto":
    running_processes = {
      *subprocess.check_output(["/usr/bin/ps", "--no-headers", "-eo", "exe"], shell = False, env = hide_kernel_threads).decode("utf-8").splitlines(),
      *subprocess.check_output(["/usr/bin/ps", "--no-headers", "-eo", "args"], shell = False, env = hide_kernel_threads).decode("utf-8").splitlines()
    }
    new_freq = int(state["base"])
    for expr, speed in freq_by_process.items():
      if speed > new_freq and any(expr in proc for proc in running_processes):
        new_freq = speed
  else:
    raise ValueError("invalid mode")

  subprocess.check_output(["/usr/bin/cpupower", "frequency-set", "-u", f"{new_freq}MHz"])
  time.sleep(5)
