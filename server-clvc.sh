#/usr/bin/env bash

cvlc "${1}" \
	--sout="#rtp{sdp=rtsp://:8554/test}" \
	--sout-rtp-mp4a-latm \
	--no-sout-rtp-sap \
	--no-sout-standard-sap \
	--ttl=1 \
	--sout-keep
