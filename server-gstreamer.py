#!/usr/bin/env python3
#vimrun! ./server-gstreamer.py

import gi
import signal
import threading
import sys
import os
import shlex

gi.require_version("Gst", "1.0")
gi.require_version("GstRtspServer", "1.0")

from gi.repository import Gst, GstRtspServer, GObject, GLib

Gst.init(None)

"""
class ExampleRtspMediaFactory(GstRtspServer.RTSPMediaFactory):
	def __init__(self):
		super().__init__()
		self.frame_count = 0
		self.jump_offset = 0
		self.inject_jump_at = None  # when to apply jump
		self.jump_applied = False

	def simulate_timestamp_jump(self, offset_ns, trigger_at_frame=30):
		# Simulate a timestamp jump by offset_ns nanoseconds at frame X.
		self.jump_offset = offset_ns
		self.inject_jump_at = trigger_at_frame
		self.jump_applied = False

	def on_prepared(self, media):
		element = media.get_element()
		payloader = element.get_by_name("pay0")
		pad = payloader.get_static_pad("src")

		# Add probe for timestamp manipulation
		pad.add_probe(Gst.PadProbeType.BUFFER, self.timestamp_jump_probe)

	def timestamp_jump_probe(self, pad, info):
		if info.type & Gst.PadProbeType.BUFFER:
			buf = info.get_buffer()

			if not buf:
				return Gst.PadProbeReturn.OK

			print(f"[Frame {self.frame_count}] Original PTS: {buf.pts}")

			# Simulate jump
			if self.inject_jump_at is not None and self.frame_count == self.inject_jump_at and not self.jump_applied:
				print(f"*** SIMULATING TIME JUMP: +{self.jump_offset / 1e9:.2f} sec ***")

				buf.pts += self.jump_offset
				self.jump_applied = True

			else:
				# normal PTS or already jumped
				pass

			print(f"[Frame {self.frame_count}] New PTS: {buf.pts}")

			self.frame_count += 1

		return Gst.PadProbeReturn.OK
"""

class DropRTSPMediaFactory(GstRtspServer.RTSPMediaFactory):
	def __init__(self):
		super().__init__()

		self.drop_count = 0

	def drop_frames(self, n):
		print(f"[drop_frames] Request to drop next {n} frames")

		self.drop_count += n

	def do_configure(self, media):
		media.connect("prepared", self.on_prepared)

	def on_prepared(self, media):
		element = media.get_element()

		if not element:
			print("[on_prepared] Failed to get media element")

			return

		payloader = element.get_by_name("pay0")

		if not payloader:
			print("[on_prepared] Named payloader 'pay0' not found")

			return

		pad = payloader.get_static_pad("src")

		if not pad:
			print("[on_prepared] Could not get 'src' pad of pay0")

			return

		print("[on_prepared] Attaching drop probe to pay0:src")

		pad.add_probe(Gst.PadProbeType.BUFFER, self.drop_probe)

	def drop_probe(self, pad, info):
		if self.drop_count > 0:
			self.drop_count -= 1

			print(f"[drop_probe] Dropping frame... {self.drop_count} left")

			return Gst.PadProbeReturn.DROP

		return Gst.PadProbeReturn.OK

class InteractiveRTSPServer:
	def __init__(self):
		self.server = GstRtspServer.RTSPServer()
		self.factory = DropRTSPMediaFactory()
		self.factory.set_launch(self._pipeline())
		self.factory.set_shared(True)
		self.server.get_mount_points().add_factory("/test", self.factory)

		self._pad_probe_id = None
		self._media = None

	def start(self):
		self.server.attach(None)
		self.factory.connect("media-configure", self._on_media_configure)

	def _on_media_configure(self, factory, media):
		def _on_prepared(media_obj):
			pipeline = media_obj.get_element()
			src = pipeline.get_by_name("videotestsrc0")

			if src:
				pad = src.get_static_pad("src")

				self._pad = pad
				self._media = media_obj

		media.connect("prepared", _on_prepared)

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
	def unpause(self):
		if self._pad and self._pad_probe_id:
			print("[server] Resuming stream...")

			self._pad.remove_probe(self._pad_probe_id)
			self._pad_probe_id = None

	def drop(self, count):
		print(f"[server] Request to drop next {count} frames")

		self.factory.drop_count = count

	def _pipeline(self):
		"""
		pipeline = (
			# Creates a "test" source.
			# https://gstreamer.freedesktop.org/documentation/videotestsrc/?gi-language=c
			# f"videotestsrc is-live=true pattern={self._patterns()}",
			f"videotestsrc is-live=true pattern={self._patterns()}",

			# Adds some simulated lag/latency.
			# https://gstreamer.freedesktop.org/documentation/coreelements/identity.html?gi-language=c
			# "identity sleep-time=100000",
			# "identity name=dropper signal-handoffs=true",

			# Encodes into H.264 video.
			# https://gstreamer.freedesktop.org/documentation/x264/index.html?gi-language=c
			"x264enc tune=zerolatency",

			# Packs input into RTP packets for RTSP; "pt" it "payload type."
			# https://gstreamer.freedesktop.org/documentation/rtp/rtph264pay.html?gi-language=c
			"rtph264pay name=pay0 pt=96"
		)
		"""

		pipeline = (
			"videotestsrc pattern=ball is-live=true",

			# Begins the process of manipulating framerate (I think)?
			# https://gstreamer.freedesktop.org/documentation/videorate/?gi-language=c
			"videorate drop-only=true",

			# Force low framerate of 10FPS.
			# https://gstreamer.freedesktop.org/documentation/additional/design/mediatype-video-raw.html?gi-language=c
			"video/x-raw,framerate=15/1",

			# https://gstreamer.freedesktop.org/documentation/pango/timeoverlay.html?gi-language=c
			# "timeoverlay halign=left valign=bottom font-desc=\"Sans, 24\"",
			"timeoverlay",

			# Force a SMALL queue, potentially adding more latency (I think)?
			# https://gstreamer.freedesktop.org/documentation/coreelements/queue.html?gi-language=c
			"queue max-size-buffers=2",

			"x264enc tune=zerolatency",

			"rtph264pay name=pay0 pt=96"
		)

		p = "( " + " ! ".join(pipeline) + " )"

		print(f"Using pipeline: {p}")

		return p

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

		# TODO: Make this random!
		return "ball"

def command_loop(server):
	print("[input] Type commands: pause / unpause / exit / drop <count>")

	while True:
		try:
			tokens = shlex.split(sys.stdin.readline().strip().lower())
			cmd, *args = tokens if tokens else ("help", [])

			if cmd == "pause":
				server.pause()

			elif cmd == "unpause":
				server.unpause()

			elif cmd == "drop":
				server.drop(len(args) and int(args[0]) or 10)

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
