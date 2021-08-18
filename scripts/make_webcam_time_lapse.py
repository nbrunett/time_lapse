"""
This is a script for making time lapse movies with the webcam on the
local computer. It captures still frame images on the local computer and
combines them into a video on the server. This means that the server
must be accessible through ssh when running this script to automatically
produce the final output video. The original frame files on the local
computer will remain on disk after the script finishes, so it is up to
you to remove them when appropriate.

Steps to run the script are the following.

  1) Set the `capture_duration_seconds` variable to the length of time
     to spend capturing frames, in seconds. This is the actual time that
     elapses while capturing frames.
  2) Set the `movie_duration_seconds` variable to the length of the
     final output video, in seconds. This is how long the video that is
     made up of the sequence of frames will play.
  3) Set the `movie_fps` variable to the frame rate of the final output
     video, in frames per second.
  4) Position the webcam so the subject is in frame.
  5) Begin capturing by running at the CLI with
    $ python make_webcam_time_lapse.py

Steps carried out by the script are the following.

  1) Capture frames and save them as PNGs in
     `local_work_dir`/<start_date_time>_webcam_frames/ (where
     `local_work_dir` is from network_config.yml).
     where <start_date_time> will be the date and time the script was
     started, formatted as YYYY-MM-DD_HH-MM-SS.
  2) Copy the frame files from the local computer to a temporary
     directory on the server.
  3) Combine the frame files into a video file on the server with
     ffmpeg, run through ssh.
  4) Copy the video file from the server to the local computer in
     `local_work_dir` from network_config.yml.
  5) Remove frame files, video file, and temporary working directory on
     the server. Does not remove the original frame files stored on the
     local computer.
"""
import cv2
from datetime import datetime
import time
import os
import subprocess
import yaml

with open("network_config.yml", "r") as network_f:
    network = yaml.load(network_f)

with open("webcam_parameters.yml", "r") as parameters_f:
    video_parameters = yaml.load(parameters_f)

# Capture frames.
start_date_time = datetime.now()
start_date_time_str = start_date_time.strftime("%Y-%M-%d_%H-%M-%S")
frame_dir_basename = f"{start_date_time_str}_webcam_frames"
os.mkdir(f"{network['local_work_dir']}{frame_dir_basename}")

frame_duration = video_parameters["capture_duration_seconds"] / (video_parameters["video_duration_seconds"] * video_parameters["video_fps"])
n_frames = int(video_parameters["video_duration_seconds"] * video_parameters["video_fps"])

print()
print("Starting camera.")
cam = cv2.VideoCapture(0)
time.sleep(0.5)

print("Capturing frames.")
for i in range(n_frames):
    ret, frame = cam.read()
    cv2.imwrite(
        f"{network['local_work_dir']}{frame_dir_basename}/{i:04d}.png",
        frame,
        [cv2.IMWRITE_PNG_COMPRESSION, 9],
    )
    time.sleep(frame_duration)
time.sleep(0.5)

print("Releasing camera.")
print()
cam.release()

# Combine frames into video.
subprocess.run(["ssh", network["server_ip"], "mkdir", network["server_work_dir"]])

print(f"Transferring frames from network['local_name'] to network['server_name'].")
subprocess.run(
    [
        "rsync",
        "--recursive",
        "--info=progress2",
        f"{network['local_work_dir']}{frame_dir_basename}",
        f"{network['server_ip']}:{network['server_work_dir']}",
    ],
)

print(f"Combining frames into video on network['server_name'].")
subprocess.run(
    [
        "ssh",
        network["server_ip"],
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-stats",
        "-framerate",
        "30",
        "-i",
        f"{network['server_work_dir']}{frame_dir_basename}/%04d.png",
        "-pix_fmt",
        "yuv420p",
        f"{network['server_work_dir']}{start_date_time_str}.mp4",
    ],
)

print(f"Transferring combined-frame video from network['server_name'] to network['local_name'].")
subprocess.run(
    [
        "rsync",
        "--info=progress2",
        f"{network['server_ip']}:{network['server_work_dir']}{start_date_time_str}.mp4",
        f"{network['local_work_dir'][:-1]}",
    ],
)

print(f"Removing intermediate files on network['server_name'].")
subprocess.run(["ssh", network["server_ip"], "rm", "-r", "-f", network["server_work_dir"]])
