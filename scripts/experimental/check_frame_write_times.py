import matplotlib.pyplot as plt
import numpy as np
import yaml

with open("network_config.yml", "r") as network_f:
    network = yaml.load(network_f)

work_dir = f"network['local_work_dir']burst_test/"

frame_read_times = np.loadtxt(f"{work_dir}frame_read_times.txt")
frame_write_times = np.loadtxt(f"{work_dir}frame_write_times.txt")

fig = plt.figure()
ax = fig.add_subplot(111)

ax.plot(
    frame_read_times - np.min(frame_read_times),
    range(len(frame_read_times)),
    marker="o",
    linestyle="None",
    label="Read",
)
ax.plot(
    frame_write_times - np.min(frame_read_times),
    range(len(frame_write_times)),
    marker="o",
    linestyle="None",
    label="Write",
)

ax.legend()
ax.grid(True)
ax.set_xlabel("Time since first frame read (s)")
ax.set_ylabel("Frame index")

plt.show()
