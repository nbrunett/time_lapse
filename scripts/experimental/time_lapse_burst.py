import cv2
import numpy as np
import os
import time
import yaml

'''
Testing making bursts of frames to stack for each output movie frame.
'''

with open("network_config.yml", "r") as network_f:
    network = yaml.load(network_f)

with open("webcam_parameters.yml", "r") as parameters_f:
    video_parameters = yaml.load(parameters_f)

################################################################################
# User settings.
work_dir = f"network['local_work_dir']overnight_jul_31_2020/"
n_frames_per_burst = 10
################################################################################

frame_spacing_sec = video_parameters["capture_duration_seconds"] / (video_parameters["video_duration_seconds"] * video_parameters["video_fps"])
movie_n_frames = int(video_parameters["video_duration_seconds"] * video_parameters["video_fps"])
tot_n_frames = int(video_parameters["video_duration_seconds"] * video_parameters["video_fps"] * n_frames_per_burst)
movie_n_frames_str_width = len(str(movie_n_frames))

frame_read_times = np.zeros(tot_n_frames)
frame_write_times = np.zeros(movie_n_frames)

ret_codes = np.zeros(n_frames_per_burst, dtype=int)
burst_frames = np.zeros((n_frames_per_burst, 720, 1280, 3))

# create frame output directory
os.mkdir(work_dir)

# open camera
print("")
print("Starting camera.")
cam = cv2.VideoCapture(0)
time.sleep(0.5)

# take exposures
print("Beginning frame capturing.")
for i in range(movie_n_frames):
    for j in range(n_frames_per_burst):
        read_ind = j + i * n_frames_per_burst
        ret_codes[j], burst_frames[j] = cam.read()
        frame_read_times[read_ind] = time.time()

    median_frame = np.median(burst_frames, axis=0)
    cv2.imwrite(
        f"{work_dir}{i:0{movie_n_frames_str_width}d}.png",
        median_frame,
        [cv2.IMWRITE_PNG_COMPRESSION, 9],
    )
    frame_write_times[i] = time.time()

    time_since_last_read = time.time() - frame_read_times[read_ind]
    time.sleep(frame_spacing_sec - time_since_last_read)

print("Finished frame capturing.")
time.sleep(0.5)

print("Releasing camera.")
print("")
cam.release()

np.savetxt(f"{work_dir}frame_read_times.txt", frame_read_times)
np.savetxt(f"{work_dir}frame_write_times.txt", frame_write_times)
