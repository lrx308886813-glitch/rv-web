#!/bin/sh

set -u

WIDTH="${WIDTH:-1920}"
HEIGHT="${HEIGHT:-1080}"
CAMID="${CAMID:-0}"
CODEC="${CODEC:-h264}"
BITRATE="${BITRATE:-4096}"
STOP_DEFAULT_APP="${STOP_DEFAULT_APP:-1}"
START_ETH="${START_ETH:-1}"
START_WIFI="${START_WIFI:-1}"
IP_WAIT_SECONDS="${IP_WAIT_SECONDS:-10}"
PID_FILE="${PID_FILE:-/var/run/custom_rtsp_streamer.pid}"
LOG_FILE="${LOG_FILE:-/tmp/custom_rtsp_streamer.log}"
RTSP_PATH="/live/0"
RTSP_PORT="554"

log() {
	echo "[custom-rtsp] $*"
}

find_bin() {
	for item in "${BIN:-}" /oem/usr/bin/custom_rtsp_streamer /usr/bin/custom_rtsp_streamer ./custom_rtsp_streamer; do
		if [ -n "$item" ] && [ -x "$item" ]; then
			echo "$item"
			return 0
		fi
	done
	return 1
}

find_iq_dir() {
	for item in "${IQ_DIR:-}" /etc/iqfiles /oem/usr/share/iqfiles /usr/share/iqfiles; do
		if [ -n "$item" ] && [ -d "$item" ]; then
			echo "$item"
			return 0
		fi
	done
	echo "${IQ_DIR:-/etc/iqfiles}"
}

get_ip() {
	dev="$1"
	ipaddr=""
	if command -v ip >/dev/null 2>&1; then
		ipaddr="$(ip -4 addr show "$dev" 2>/dev/null | awk '/inet / { sub(/\/.*/, "", $2); print $2; exit }')"
	fi
	if [ -n "$ipaddr" ]; then
		echo "$ipaddr"
		return 0
	fi
	ifconfig "$dev" 2>/dev/null | awk '
		/inet addr:/ { sub(/.*addr:/, "", $2); print $2; exit }
		/inet / { print $2; exit }
	'
}

stop_default_camera_app() {
	if [ "$STOP_DEFAULT_APP" != "1" ]; then
		return 0
	fi

	log "stop default camera apps to release VI/VENC resources"
	/etc/init.d/S21appinit stop >/dev/null 2>&1 || true
	killall rkipc >/dev/null 2>&1 || true
	killall smart_door >/dev/null 2>&1 || true
	killall simple_vi_bind_venc_rtsp >/dev/null 2>&1 || true
	killall custom_rtsp_streamer >/dev/null 2>&1 || true
	rm -f "$PID_FILE"
	sleep 1
}

start_eth() {
	if [ "$START_ETH" != "1" ]; then
		return 0
	fi

	log "bring up eth0"
	ifconfig eth0 up >/dev/null 2>&1 || true
	if command -v udhcpc >/dev/null 2>&1; then
		udhcpc -i eth0 -T 1 -A 0 -b -q >/dev/null 2>&1 || true
	fi
}

write_wifi_config_from_env() {
	if [ -z "${WIFI_SSID:-}" ]; then
		return 0
	fi

	mkdir -p /data/cfg
	cat >/data/cfg/wpa_supplicant.conf <<EOF
ctrl_interface=/var/run/wpa_supplicant
ap_scan=1
update_config=1

network={
	ssid="$WIFI_SSID"
	psk="${WIFI_PSK:-}"
	key_mgmt=WPA-PSK
}
EOF
}

start_wifi() {
	if [ "$START_WIFI" != "1" ]; then
		return 0
	fi

	log "bring up wlan0"
	if [ -x /oem/usr/ko/insmod_wifi.sh ]; then
		/oem/usr/ko/insmod_wifi.sh 0 "${RK_ENABLE_WIFI_CHIP:-}" >/dev/null 2>&1 || true
	fi

	write_wifi_config_from_env
	ifconfig wlan0 up >/dev/null 2>&1 || true
	mkdir -p /var/run/wpa_supplicant

	WIFI_CONF=""
	if [ -f /data/cfg/wpa_supplicant.conf ]; then
		WIFI_CONF="/data/cfg/wpa_supplicant.conf"
	elif [ -f /etc/wpa_supplicant.conf ]; then
		WIFI_CONF="/etc/wpa_supplicant.conf"
	elif [ -f /data/wpa_supplicant.conf ]; then
		WIFI_CONF="/data/wpa_supplicant.conf"
	fi

	if [ -z "$WIFI_CONF" ]; then
		log "skip WiFi: no wpa_supplicant.conf. Set WIFI_SSID and WIFI_PSK when running this script."
		return 0
	fi

	killall wpa_supplicant >/dev/null 2>&1 || true
	wpa_supplicant -B -i wlan0 -c "$WIFI_CONF" >/tmp/custom_rtsp_wifi.log 2>&1 || true
	if command -v udhcpc >/dev/null 2>&1; then
		udhcpc -i wlan0 -T 1 -A 0 -b -q >/dev/null 2>&1 || true
	fi
}

print_urls() {
	found=0
	for dev in eth0 wlan0; do
		ipaddr="$(get_ip "$dev")"
		if [ -n "$ipaddr" ]; then
			log "$dev RTSP: rtsp://$ipaddr:$RTSP_PORT$RTSP_PATH"
			found=1
		fi
	done

	if [ "$found" = "0" ]; then
		log "no IPv4 address found yet; check ifconfig, wpa_cli -i wlan0 status, or DHCP."
	fi
}

wait_for_any_ip() {
	i=0
	while [ "$i" -lt "$IP_WAIT_SECONDS" ]; do
		for dev in eth0 wlan0; do
			if [ -n "$(get_ip "$dev")" ]; then
				return 0
			fi
		done
		sleep 1
		i=$((i + 1))
	done
	return 0
}

BIN_PATH="$(find_bin)" || {
	log "custom_rtsp_streamer not found. Build app and install it to /oem/usr/bin first."
	exit 1
}
IQ_PATH="$(find_iq_dir)"

stop_default_camera_app
start_eth
start_wifi

mkdir -p "$(dirname "$PID_FILE")"
rm -f "$LOG_FILE"

log "start encoder: ${WIDTH}x${HEIGHT}, codec=${CODEC}, bitrate=${BITRATE}Kbps, camid=${CAMID}, iq=${IQ_PATH}"
"$BIN_PATH" -I "$CAMID" -w "$WIDTH" -h "$HEIGHT" -e "$CODEC" -b "$BITRATE" -a "$IQ_PATH" >"$LOG_FILE" 2>&1 &
echo "$!" >"$PID_FILE"
sleep 1

if kill -0 "$(cat "$PID_FILE")" >/dev/null 2>&1; then
	log "streamer pid=$(cat "$PID_FILE"), log=$LOG_FILE"
	wait_for_any_ip
	print_urls
else
	log "streamer failed to start. Last log:"
	tail -n 40 "$LOG_FILE" 2>/dev/null || true
	rm -f "$PID_FILE"
	exit 1
fi
