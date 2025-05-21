#!/usr/bin/env python3
#vimrun! ./server-gstreamer.py

import gi
import signal
import threading
import sys
import os

gi.require_version("Gst", "1.0")
gi.require_version("GstRtspServer", "1.0")

from gi.repository import Gst, GstRtspServer, GObject, GLib

Gst.init(None)

class InteractiveRTSPServer:
	def __init__(self):
		self.server = GstRtspServer.RTSPServer()
		self.factory = GstRtspServer.RTSPMediaFactory()
		self.factory.set_launch(self._launch_pipeline())
		self.factory.set_shared(True)
		self.server.get_mount_points().add_factory("/test", self.factory)

		self._pad_probe_id = None
		self._media = None

	def start(self):
		self.server.attach(None)
		self.factory.connect("media-configure", self.on_media_configure)

	def on_media_configure(self, factory, media):
		def on_prepared(media_obj):
			pipeline = media_obj.get_element()
			src = pipeline.get_by_name("videotestsrc0")

			if src:
				pad = src.get_static_pad("src")
				self._pad = pad
				self._media = media_obj

		media.connect("prepared", on_prepared)

	# def stop(self):
	# 	print("[server] Stopping stream...")
    #
	# 	self.server.quit()

	def pause(self):
		if self._pad and not self._pad_probe_id:

			print("[server] Pausing stream...")

			def block_cb(pad, info):
				return Gst.PadProbeReturn.OK

			self._pad_probe_id = self._pad.add_probe(Gst.PadProbeType.BLOCK, block_cb)

	# TODO: Move this behavior up into `pause()`, and make it a "toggle."
	def restore(self):
		if self._pad and self._pad_probe_id:
			print("[server] Resuming stream...")

			self._pad.remove_probe(self._pad_probe_id)
			self._pad_probe_id = None

	def _launch_pipeline(self):
		return(
			f"( videotestsrc pattern={self._patterns()} "
			"! x264enc tune=zerolatency "
			"! rtph264pay name=pay0 pt=96 )"
		)

		# return(
		# 	"( videotestsrc is-live=true pattern=smpte "
		# 	"! video/x-raw,width=640,height=480,framerate=30/1 "
		# 	"! x264enc tune=zerolatency bitrate=512 speed-preset=superfast "
		# 	"! rtph264pay config-interval=1 name=pay0 pt=96 )"
		# )

	def _patterns(self):
		"""
		smpte             | SMPTE color bars
		snow              | Static noise (TV snow)
		black             | Solid black
		white             | Solid white
		red               | Solid red
		green             | Solid green
		blue              | Solid blue
		checkers-1        | Small checkerboard
		checkers-2        | Large checkerboard
		checkers-4        | Huge checkerboard
		checkers-8        | Giant checkerboard
		circular          | Radial rings, like a ripple
		zone-plate        | Zone plate pattern (tests resolution)
		gamut             | Color test to reveal out-of-gamut RGB
		chroma-zone-plate | Zone plate using chroma variation
		solid-color       | Uses the foreground-color property
		ball              | Bouncing colored ball on a background
		smpte100          | 100% SMPTE color bars
		bar               | Vertical color bars (basic)
		pinwheel          | Rotating RGB pinwheel
		blinking          | Alternating colors (blinks)
		moving-bar        | Color bar that scrolls left to right
		pluge             | Tests luminance contrast
		colors            | Combination color pattern
		test-pattern      | Pattern designed for video analysis tools
		"""

		# TODO: What else?
		return "ball"

# GLib.timeout_add_seconds(10, stop_stream)

def command_loop(server):
	print("[input] Type commands: pause / unpause / exit")

	while True:
		try:
			cmd = sys.stdin.readline().strip().lower()

			if cmd == "pause":
				server.pause()

			elif cmd == "unpause":
				server.unpause()

			elif cmd == "exit":
				print("[input] Exiting...")

				# TODO: Why is this necessary (and not `sys.exit(0)`)? Is it because of the thread?
				os._exit(0)

			else:
				print(f"[input] Unknown command: {cmd}")

		except Exception as e:
			print(f"[input] Error: {e}")

def main():
	server = InteractiveRTSPServer()
	loop = GLib.MainLoop()

	def handle_sigint(sig, frame):
		print("\nShutting down RTSP server...")

		loop.quit()

	signal.signal(signal.SIGINT, handle_sigint)

	try:
		server.start()

		threading.Thread(target=command_loop, args=(server,), daemon=True).start()

		loop.run()

	except KeyboardInterrupt:
		print("\nInterrupted. Cleaning up...")

		loop.quit()

		sys.exit(0)

if __name__ == "__main__":
	main()
