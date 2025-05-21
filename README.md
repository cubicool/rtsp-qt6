# rtsp-qt6

Demos Using QT6 &amp; VLC/FFmpeg RTSP

# Usage

You'll need to create a test video and host an RTSP server (however you want).
Personally, I used `cvlc` for this, and included a small wrapper script called
`server-cvlc.sh` in this repo for that purpose.

## Python Server
There is ALSO a `server-gstreamer.py` script that wraps the GStreamer pipeline,
providing a CLI for stopping/starting/pausing the RTSP server. In the future it
will have commands for instroducing arbitrary latency, dropped frames, etc., to
help test the robustnes of the QT6 RTSP examples.

## FFmpeg CLI Conversion

If you have some existing video you want to convert and host, use a command like
the following:

```sh
ffmpeg -i input.mp4 -vf scale=640:480 -c:v libvpx -crf 10 -b:v 1M -c:a libvorbis -t 30 output.webm
```

*NOTE*: In the above command, the `-t 30` argument only encodes the first 30
seconds!
