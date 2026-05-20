#!/bin/sh

set -u

PID_FILE="${PID_FILE:-/var/run/custom_rtsp_streamer.pid}"

log() {
	echo "[custom-rtsp] $*"
}

stop_pid() {
	pid="$1"
	if [ -z "$pid" ]; then
		return 0
	fi

	if kill -0 "$pid" >/dev/null 2>&1; then
		log "stop pid=$pid"
		kill "$pid" >/dev/null 2>&1 || true
		i=0
		while kill -0 "$pid" >/dev/null 2>&1 && [ "$i" -lt 10 ]; do
			sleep 1
			i=$((i + 1))
		done
		if kill -0 "$pid" >/dev/null 2>&1; then
			log "force stop pid=$pid"
			kill -9 "$pid" >/dev/null 2>&1 || true
		fi
	fi
}

if [ -f "$PID_FILE" ]; then
	stop_pid "$(cat "$PID_FILE" 2>/dev/null)"
	rm -f "$PID_FILE"
fi

killall custom_rtsp_streamer >/dev/null 2>&1 || true
killall simple_vi_bind_venc_rtsp >/dev/null 2>&1 || true

log "stopped"
