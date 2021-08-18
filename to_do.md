# General

- deal with YML-reading warning

# `convert_camcorder_videos_to_time_lapse.py`

- gracefully fail if /Volumes/Untitled/PRIVATE/AVCHD/BDMV/STREAM isn't found
- concatenated files get named with the date from the first file in the list
- concatenated files get exif metadata from the first file for things like datetimeoriginal, but gets the date and time of when it was created in the modified time or whatever tag makes sense for edited video
- factor out into functions
- add switch to do lightning finding
- try some parallelization
  - one process transfers while another calculates threshold for lightning frames

# `make_webcam_time_lapse.py`

- add ability to retransfer individual frame files from local computer to server to recombine into a video file
  - this would be for the case where frames were captured and combined but I want to try combining already-existing frames in a different way
    - frames are not removed at the end of this script so there should be a way to work with just the frames if I want to tweak the output video
  - not sure this needs to be in this script but it is related to it's process right now