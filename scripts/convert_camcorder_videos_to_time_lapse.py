"""
Script to automate most of the process of making timelapse videos from
videos shot with the digital camcorder. The majority of the work is done
on the server, so it has to be run when it is accessible, and it assumes
the files are coming from the SD card plugged directly into the local
computer.

When long videos are recorded, multiple files are sometimes created that
are meant to be run one after the other to show the full recording.
After the videos are sped up, concatenation of these multi-file videos
is automatically carried out (see below for more detail).

This will work when there are multiple separate videos on the SD card to
be sped up. The script will ask for the speed-up factor for each video
and videos can also be skipped entirely (see below for more detail).

Steps carried out in this script are the following.

  1)  Open a Finder window in the SD directory where the video files
      are stored.
  2)  Prompt the user for speed-up factors for each MTS file found on
      the SD card. Files can also be skipped so they will not be
      processed by this script at all. This is the only manual portion
      of the process.
  3)  Copy video files from the SD card to a temporary directory on
      server with rsync.
  4)  Speed up the videos on server with ffmpeg run through ssh.
  5)  Check for files that need to be concatenated based on the amount
      of time between the end of one video and the start of the next.
      Start times and durations are extracted on server with
      exiftool.
  6)  Create temporary concatenation file list text files on local
      computer if any files need to be combined.
  7)  Copy concatenation file list files to server with rsync.
  8)  Concatenate appropriate video files on server with ffmpeg.
  9)  Add the CreateDate tag yyyy-mm-dd to all sped-up video file names.
  10) Copy sped-up files from server to local computer in local_work_dir
      from network_config.yml.
  11) Remove original-speed files, sped-up files, and temporary working
      directory on server. Also remove concatenation file list files
      on local computer.
"""
from datetime import datetime
from datetime import timedelta
import glob
import numpy as np
import os
import subprocess
import yaml

with open("network_config.yml", "r") as network_f:
    network = yaml.load(network_f)

subprocess.run(["open", network["sd_dir"]])

mts_files = sorted(glob.glob(f"{network['sd_dir']}*.MTS"))
speed_up_prompt = 'Enter speed-up factor for {:} or "s" to skip this file. '
speed_up_responses = list()
for mts_file in mts_files:
    mts_basename = os.path.basename(mts_file)
    while True:
        the_input = input(speed_up_prompt.format(mts_basename))
        if the_input.lower() == "s":
            speed_up_responses.append("s")
            break
        try:
            speed_up_responses.append(float(the_input))
            break
        except:
            print("Did not recognize input.")

files_to_speed_up = list()
basenames_to_speed_up = list()
sped_up_basenames = list()
speed_up_factors = list()
for i in range(len(speed_up_responses)):
    if speed_up_responses[i] != "s":
        file_basename = os.path.basename(mts_files[i])
        file_name, _ = os.path.splitext(file_basename)
        files_to_speed_up.append(mts_files[i])
        basenames_to_speed_up.append(file_basename)
        sped_up_basenames.append(f"{file_name}_fast.mp4")
        speed_up_factors.append(speed_up_responses[i])

print(f"Transferring original videos from {network['local_name']} to {network['server_name']}.")
subprocess.run(["ssh", network["server_ip"], "mkdir", network["server_work_dir"]])
subprocess.run(
    ["rsync", "--info=progress2"] + files_to_speed_up + [f"{network['server_ip']}:{network['server_work_dir']}"],
)

print(f"Speeding up videos on {network['server_name']}.")
# get original file start and end times for adding create date to video names
# and checking for the need for video concatenation
file_to_speed_up_starts = list()
file_to_speed_up_ends = list()
sped_up_dated_basenames = sped_up_basenames.copy()
for i in range(len(basenames_to_speed_up)):
    exiftool_proc = subprocess.run(
        [
            "ssh",
            network["server_ip"],
            "exiftool",
            "--printConv",
            "-table",
            "-datetimeOriginal",
            "-duration",
            f"{network['server_work_dir']}{basenames_to_speed_up[i]}",
        ],
        capture_output=True,
    )
    (
        datetime_original_str,
        duration_str,
    ) = exiftool_proc.stdout.split(b"\t")
    start = datetime.strptime(
        datetime_original_str.decode(), "%Y:%m:%d %H:%M:%S%z",
    )
    duration = timedelta(seconds=float(duration_str.strip()))
    file_to_speed_up_starts.append(start)
    file_to_speed_up_ends.append(start + duration)
    sped_up_dated_basenames[i] = start.strftime("%Y_%b_%d_") + sped_up_dated_basenames[i]

# speed up files with ffmpeg
ffmpeg_command_first_half = [
    "ffmpeg", "-hide_banner", "-loglevel", "error", "-stats",
]
for i in range(len(files_to_speed_up)):
    ffmpeg_command_last_half = [
        "-i",
        f"{network['server_work_dir']}{basenames_to_speed_up[i]}",
        '-an',
        '-filter:v',
        f'"setpts=PTS/{speed_up_factors[i]}"',
        f'{network["server_work_dir"]}{sped_up_dated_basenames[i]}',
    ]
    print(f"  {basenames_to_speed_up[i]}")
    subprocess.run(
        ["ssh", network["server_ip"]] + ffmpeg_command_first_half + ffmpeg_command_last_half,
    )
    print()

print("Checking for videos that need to be concatenated.")
# assign grouping indices to files
sorted_starts_idx = np.argsort(file_to_speed_up_starts)
group_idx = 0
file_to_speed_up_group_idx = [group_idx]
for i in range(len(sorted_starts_idx) - 1):
    file_pair_time_diff = (
        file_to_speed_up_starts[sorted_starts_idx[i + 1]]
        - file_to_speed_up_ends[sorted_starts_idx[i]]
    )
    if file_pair_time_diff.total_seconds() > 1.5:
        group_idx += 1
    file_to_speed_up_group_idx.append(group_idx)

unique_group_idx, group_idx_counts = np.unique(
    file_to_speed_up_group_idx, return_counts=True,
)
basenames_to_return = sped_up_dated_basenames.copy()
if len(unique_group_idx) == len(files_to_speed_up):
    print("Did not find any videos that need concatenation.")
else:
    print("Concatenating sped-up videos.")
    # make concatenation filename list files for ffmpeg
    for i in range(len(unique_group_idx)):
        if group_idx_counts[i] > 1:
            with open(f"{network['local_work_dir']}concat_group_{unique_group_idx[i]}.txt", "w") as f:
                for idx in np.where(file_to_speed_up_group_idx == unique_group_idx[i])[0]:
                    f.write(f"file '{network['server_work_dir']}{sped_up_dated_basenames[idx]}'\n")
                    basenames_to_return.remove(sped_up_dated_basenames[idx])

    # send concatenation list files to server
    concat_list_files = glob.glob(f"{network['local_work_dir']}concat_group_*.txt")
    subprocess.run(
        ["rsync"] + concat_list_files + [f"{network['server_ip']}:{network['server_work_dir']}"],
    )

    # concatenate files with ffmpeg
    for f in concat_list_files:
        concat_list_basename = os.path.basename(f)
        concat_list_file_name, _ = os.path.splitext(concat_list_basename)
        subprocess.run(
            [
                "ssh",
                network["server_ip"],
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-stats",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                f"{network['server_work_dir']}{concat_list_basename}",
                "-c",
                "copy",
                f"{network['server_work_dir']}{concat_list_file_name}_fast.mp4",
            ],
        )
        basenames_to_return.append(f"{concat_list_file_name}_fast.mp4")

print(f"Transferring sped-up videos from {network['server_name']} to {network['local_name']}.")
network_return_files = [f"{network['server_ip']}:{network['server_work_dir']}{f}" for f in basenames_to_return]
subprocess.run(
    ["rsync", "--info=progress2"] + network_return_files + [network["local_work_dir"]],
)

# remove concatenation list files from local computer
if len(concat_list_files) > 0:
    for f in concat_list_files:
        os.remove(f)

print(f"Removing intermediate files on {network['server_name']}.")
subprocess.run(["ssh", network["server_ip"], "rm", "-r", "-f", network["server_work_dir"]])
