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

class DropRTSPMediaFactory(GstRtspServer.RTSPMediaFactory):
	def __init__(self):
		super().__init__()

		# Members for the `drop_frames` method!
		self.drop_count = 0

		# Members for the `jump_frames` method!
		self.jump_offset = None
		self.jump_ms = None

	def drop_frames(self, n):
		print(f"[drop_frames] Request to drop next {n} frames")

		self.drop_count += n

	def jump_frames(self, ms):
		print(f"[jump_frames] Request to jump {ms}ms forward in frames")

		self.jump_ms = ms

	# This is always called when the media need to be configured (as a "virtual" method).
	def do_configure(self, media):
		def _media_prepared(media):
			element = media.get_element()

			if not element:
				print("[_media_prepared] Failed to get media element")

				return

			payloader = element.get_by_name("pay0")

			if not payloader:
				print("[_media_prepared] Named payloader 'pay0' not found")

				return

			pad = payloader.get_static_pad("src")

			if not pad:
				print("[_media_prepared] Could not get 'src' pad of pay0")

				return

			# We "install" this probe in the live above, so it ALWAYS gets run; thus, we need a sentinel
			# "member" to kick off some logic when we want to change behavior.
			def _drop_probe(pad, info):
				if self.drop_count > 0:
					self.drop_count -= 1

					print(f"[_drop_probe] Dropping frame... {self.drop_count} left")

					return Gst.PadProbeReturn.DROP

				return Gst.PadProbeReturn.OK

			print("[_media_prepared] Attaching DROP probe to pay0:src")

			pad.add_probe(Gst.PadProbeType.BUFFER, _drop_probe)

			def _jump_probe(pad, info):
				if self.jump_ms and info.type & Gst.PadProbeType.BUFFER:
					buf = info.get_buffer()

					print(f"[_jump_probe] PTS: {buf.pts}")

					self.jump_offset = buf.pts + self.jump_ms

					buf.pts += self.jump_ms

					self.jump_ms = None

				return Gst.PadProbeReturn.OK

			print("[_media_prepared] Attaching JUMP probe to pay0:src")

			pad.add_probe(Gst.PadProbeType.BUFFER, _jump_probe)

		media.connect("prepared", _media_prepared)

		def _media_unprepared(media):
			print("[_media_unprepared] ...client closed!");

		media.connect("unprepared", _media_unprepared)

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
		def _media_configure(factory, media):
			print("_media_configure")

			def _prepared(media_obj):
				pipeline = media_obj.get_element()
				src = pipeline.get_by_name("videotestsrc0")

				if src:
					pad = src.get_static_pad("src")

					self._pad = pad
					self._media = media_obj

			media.connect("prepared", _prepared)

		self.server.attach(None)
		self.factory.connect("media-configure", _media_configure)

	def pause(self):
		if self._pad and not self._pad_probe_id:
			print("[server] Pausing stream...")

			def block_probe(pad, info):
				return Gst.PadProbeReturn.OK

			self._pad_probe_id = self._pad.add_probe(Gst.PadProbeType.BLOCK, block_probe)

	# TODO: Move this behavior up into `pause()`, and make it a "toggle."
	def unpause(self):
		if self._pad and self._pad_probe_id:
			print("[server] Resuming stream...")

			self._pad.remove_probe(self._pad_probe_id)
			self._pad_probe_id = None

	def drop(self, count):
		print(f"[server] Request to drop next {count} frames")

		self.factory.drop_frames(count)

	def jump(self, ms):
		print(f"[server] Request to jump forward {ms}ms")

		self.factory.jump_frames(ms)

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
			"video/x-raw,framerate=5/1",

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
	print("[input] Type commands: pause / unpause / exit / drop <count> / jump <ms>")

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

			elif cmd == "jump":
				server.jump(len(args) and int(args[0]) or 5000)

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
