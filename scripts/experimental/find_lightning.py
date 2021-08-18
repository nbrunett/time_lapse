import cv2
import numpy as np
import os
import yaml

with open("../network_config.yml", "r") as network_f:
    network = yaml.load(network_f)

if not os.path.exists(f"{network['local_work_dir']}lightning_means_and_stdevs.txt"):
    cap = cv2.VideoCapture(f"{network['local_work_dir']}00003.MTS")
    subsample_of_means = list()
    frame_index = 0
    while True:
        success, frame = cap.read()

        if success:
            if (frame_index % 100) == 0:
                print(frame_index)
                subsample_of_means.append(np.mean(frame, axis=(0, 1)))

            frame_index += 1
        else:
            break
    cap.release()

    subsample_means = np.mean(subsample_of_means, axis=0)
    subsample_stdevs = np.std(subsample_of_means, axis=0)
    with open(f"{network['local_work_dir']}lightning_means_and_stdevs.txt", "w") as f:
        f.write("# means\n")
        f.write(f"{subsample_means}\n")
        f.write("# standard deviations\n")
        f.write(f"{subsample_stdevs}\n")

mean_and_stdev = list()
with open(f"{network['local_work_dir']}lightning_means_and_stdevs.txt", "r") as f:
    for line in f:
        if "#" not in line:
            mean_and_stdev.append(float(line.split()[0][1:]))
threshold = mean_and_stdev[0] + (3 * mean_and_stdev[1])

os.mkdir(f"{network['local_work_dir']}lightning_frames")

cap = cv2.VideoCapture(f"{network['local_work_dir']}00003.MTS")
frame_index = 0
while True:
    success, frame = cap.read()

    if success:
        if np.mean(frame[:, :, 0], axis=(0, 1)) > threshold:
            frame_path = f"{network['local_work_dir']}lightning_frames/{frame_index:03d}_lightning.png"
            cv2.imwrite(frame_path, frame)
            frame_index += 1
    else:
        break
cap.release()

cap = cv2.VideoCapture(f"{network['local_work_dir']}00004.MTS")
frame_index += 1
while True:
    success, frame = cap.read()

    if success:
        if np.mean(frame[:, :, 0], axis=(0, 1)) > threshold:
            frame_path = f"{network['local_work_dir']}lightning_frames/{frame_index:03d}_lightning.png"
            cv2.imwrite(frame_path, frame)
            frame_index += 1
    else:
        break
cap.release()
