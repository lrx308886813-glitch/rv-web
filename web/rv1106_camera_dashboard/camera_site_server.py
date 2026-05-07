from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse
import json
import os
import subprocess
import urllib.error
import urllib.request


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "mediamtx.yml"
STATE_PATH = BASE_DIR / "recording_state.json"
DEFAULT_RECORD_DIR = BASE_DIR / "recordings"
DEVICE_IP = "192.168.31.18"
ADB_PATH = r"E:\dev\ADB\platform-tools\adb.exe"
ADB_SERIAL = "192.168.31.18:5555"
STREAMS = {
    "main": "rtsp://192.168.31.18/live/0",
    "sub": "rtsp://192.168.31.18/live/1",
}
VIDEO_PRESETS = {
    "ultra": {
        "label": "超清",
        "stream": "main",
        "video.0": {"width": 2304, "height": 1296, "fps": 25, "mid_rate": 1024, "max_rate": 2048},
        "video.1": {"width": 704, "height": 576, "fps": 30, "mid_rate": 256, "max_rate": 512},
    },
    "hd": {
        "label": "高清",
        "stream": "main",
        "video.0": {"width": 1920, "height": 1080, "fps": 25, "mid_rate": 1024, "max_rate": 2048},
        "video.1": {"width": 704, "height": 576, "fps": 30, "mid_rate": 256, "max_rate": 512},
    },
    "balanced": {
        "label": "均衡",
        "stream": "main",
        "video.0": {"width": 1280, "height": 720, "fps": 25, "mid_rate": 768, "max_rate": 1536},
        "video.1": {"width": 704, "height": 576, "fps": 30, "mid_rate": 256, "max_rate": 512},
    },
    "smooth": {
        "label": "流畅",
        "stream": "sub",
        "video.0": {"width": 1280, "height": 720, "fps": 25, "mid_rate": 768, "max_rate": 1536},
        "video.1": {"width": 704, "height": 576, "fps": 30, "mid_rate": 256, "max_rate": 512},
    },
}


def _json_response(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler):
    length = int(handler.headers.get("Content-Length", "0") or "0")
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8"))


def _load_state():
    if not STATE_PATH.exists():
        return {
            "recording": False,
            "recordPath": "",
            "recordDir": str(DEFAULT_RECORD_DIR),
            "recordStream": "",
            "videoPreset": "ultra",
        }
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "recording": False,
            "recordPath": "",
            "recordDir": str(DEFAULT_RECORD_DIR),
            "recordStream": "",
            "videoPreset": "ultra",
        }


def _save_state(state):
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _adb(args, timeout=20):
    command = [ADB_PATH] + args
    completed = subprocess.run(
        command,
        cwd=str(BASE_DIR),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(detail or "ADB command failed")
    return completed.stdout


def _set_line_value(line, key, value, suffix=""):
    prefix = f"{key} = "
    return prefix + str(value) + suffix


def _patch_video_section(lines, section_name, values):
    patched = []
    current = ""
    changed_keys = set()
    key_values = {
        "width": values["width"],
        "height": values["height"],
        "src_frame_rate_num": values["fps"],
        "dst_frame_rate_num": values["fps"],
        "mid_rate": values["mid_rate"],
        "max_rate": values["max_rate"],
        "output_data_type": "H.264",
    }
    key_values["buffer_size"] = int(values["width"] * values["height"] / 2)

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped[1:-1]

        if current == section_name and "=" in line:
            key = line.split("=", 1)[0].strip()
            if key in key_values:
                suffix = " ; w * h / 2" if key == "buffer_size" else ""
                patched.append(_set_line_value(line, key, key_values[key], suffix))
                changed_keys.add(key)
                continue

        patched.append(line)

    missing = set(key_values) - changed_keys
    if missing:
        raise RuntimeError(f"{section_name} missing keys: {', '.join(sorted(missing))}")
    return patched


def _apply_video_preset(preset_name):
    preset = VIDEO_PRESETS[preset_name]
    _adb(["connect", ADB_SERIAL], timeout=10)
    raw = _adb(["-s", ADB_SERIAL, "shell", "cat /userdata/rkipc.ini"], timeout=10)
    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines = _patch_video_section(lines, "video.0", preset["video.0"])
    lines = _patch_video_section(lines, "video.1", preset["video.1"])

    local_ini = BASE_DIR / "rkipc.generated.ini"
    local_ini.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    _adb(["-s", ADB_SERIAL, "push", str(local_ini), "/userdata/rkipc.ini"], timeout=20)
    factory_ini = _adb([
        "-s",
        ADB_SERIAL,
        "shell",
        "readlink -f /tmp/rkipc-factory-config.ini 2>/dev/null || true",
    ], timeout=10).strip()
    if factory_ini:
        _adb(["-s", ADB_SERIAL, "push", str(local_ini), factory_ini], timeout=20)
    _adb([
        "-s",
        ADB_SERIAL,
        "shell",
        "kill -9 $(pidof rkipc) 2>/dev/null; sleep 1; source /etc/profile.d/RkEnv.sh; cd /oem; start-stop-daemon -S -b -x /oem/usr/bin/rkipc -- -a /oem/usr/share/iqfiles",
    ], timeout=20)
    return {
        "preset": preset_name,
        "label": preset["label"],
        "stream": preset["stream"],
        "main": preset["video.0"],
        "sub": preset["video.1"],
    }


def _yaml_quote(value):
    return "'" + str(value).replace("\\", "/").replace("'", "''") + "'"


def _record_template(record_dir):
    return str(Path(record_dir) / "%path" / "%Y-%m-%d_%H-%M-%S-%f").replace("\\", "/")


def _write_mediamtx_config(active_stream="", record_dir=None):
    record_dir = record_dir or str(DEFAULT_RECORD_DIR)
    record_path = _record_template(record_dir)

    lines = [
        "api: yes",
        "apiAddress: 127.0.0.1:9997",
        "playback: yes",
        "playbackAddress: :9996",
        "rtspAddress: :8554",
        "hlsAddress: :8888",
        "webrtcAddress: :8889",
        "",
        "paths:",
    ]

    for name, source in STREAMS.items():
        record = "yes" if name == active_stream else "no"
        lines.extend([
            f"  {name}:",
            f"    source: {source}",
            "    rtspTransport: tcp",
            "    sourceOnDemand: yes",
            f"    record: {record}",
            f"    recordPath: {_yaml_quote(record_path)}",
            "    recordFormat: fmp4",
            "    recordPartDuration: 1s",
            "    recordSegmentDuration: 1m",
            "    recordDeleteAfter: 0s",
            "",
        ])

    CONFIG_PATH.write_text("\n".join(lines), encoding="utf-8")
    return record_path


def _pick_directory():
    command = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$dialog = New-Object System.Windows.Forms.FolderBrowserDialog; "
        "$dialog.Description = '选择录像保存目录'; "
        "$dialog.ShowNewFolderButton = $true; "
        "if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) "
        "{ [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Write-Output $dialog.SelectedPath }"
    )
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-STA", "-Command", command],
        cwd=str(BASE_DIR),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "目录选择器启动失败")
    return completed.stdout.strip()


def _open_directory(record_dir):
    path = Path(record_dir).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    os.startfile(str(path))


def _playback_list(path_name, host_name):
    url = f"http://127.0.0.1:9996/list?{urlencode({'path': path_name})}"
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            items = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code in (400, 404):
            return []
        raise
    except Exception:
        return []

    playback_host = host_name.split(":", 1)[0] or "localhost"
    rewritten = []
    for item in items:
        params = {
            "path": path_name,
            "start": item.get("start", ""),
            "duration": item.get("duration", 0),
            "format": "mp4",
        }
        copied = dict(item)
        copied["playUrl"] = f"http://{playback_host}:9996/get?{urlencode(params)}"
        rewritten.append(copied)
    return rewritten


class CameraHandler(SimpleHTTPRequestHandler):
    server_version = "RV1106Camera/1.0"

    def translate_path(self, path):
        parsed = urlparse(path)
        clean = parsed.path.lstrip("/") or "index.html"
        return str((BASE_DIR / clean).resolve())

    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            state = _load_state()
            return _json_response(self, 200, {
                "ok": True,
                "deviceIp": DEVICE_IP,
                "recording": bool(state.get("recording")),
                "recordPath": state.get("recordPath", ""),
                "recordDir": state.get("recordDir", str(DEFAULT_RECORD_DIR)),
                "recordStream": state.get("recordStream", ""),
                "videoPreset": state.get("videoPreset", "ultra"),
            })

        if parsed.path == "/api/video-settings":
            state = _load_state()
            preset_name = state.get("videoPreset", "ultra")
            preset = VIDEO_PRESETS.get(preset_name, VIDEO_PRESETS["ultra"])
            return _json_response(self, 200, {
                "ok": True,
                "preset": preset_name,
                "label": preset["label"],
                "stream": preset["stream"],
                "main": preset["video.0"],
                "sub": preset["video.1"],
            })

        if parsed.path == "/api/recordings":
            query = parse_qs(parsed.query)
            path_name = query.get("path", ["main"])[0]
            if path_name not in STREAMS:
                return _json_response(self, 400, {"error": "invalid path"})
            items = _playback_list(path_name, self.headers.get("Host", "localhost"))
            return _json_response(self, 200, {"ok": True, "items": items})

        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/pick-directory":
                selected = _pick_directory()
                state = _load_state()
                if selected:
                    state["recordDir"] = selected
                    _save_state(state)
                return _json_response(self, 200, {"ok": True, "path": selected})

            if parsed.path == "/api/open-directory":
                payload = _read_json(self)
                record_dir = payload.get("dir") or _load_state().get("recordDir") or str(DEFAULT_RECORD_DIR)
                _open_directory(record_dir)
                return _json_response(self, 200, {"ok": True, "path": record_dir})

            if parsed.path == "/api/recording/start":
                payload = _read_json(self)
                stream = payload.get("stream", "main")
                if stream not in STREAMS:
                    return _json_response(self, 400, {"error": "invalid stream"})
                record_dir = payload.get("dir") or str(DEFAULT_RECORD_DIR)
                Path(record_dir).mkdir(parents=True, exist_ok=True)
                record_path = _write_mediamtx_config(stream, record_dir)
                state = _load_state()
                state.update({
                    "recording": True,
                    "recordPath": record_path,
                    "recordDir": record_dir,
                    "recordStream": stream,
                })
                _save_state(state)
                return _json_response(self, 200, {"ok": True, "stream": stream, "recordPath": record_path})

            if parsed.path == "/api/recording/stop":
                state = _load_state()
                record_dir = state.get("recordDir") or str(DEFAULT_RECORD_DIR)
                _write_mediamtx_config("", record_dir)
                state.update({
                    "recording": False,
                    "recordPath": "",
                    "recordStream": "",
                    "recordDir": record_dir,
                })
                _save_state(state)
                return _json_response(self, 200, {"ok": True, "recordDir": record_dir})

            if parsed.path == "/api/video-preset":
                state = _load_state()
                if state.get("recording"):
                    return _json_response(self, 409, {"error": "录制中不能切换画质，先停止录制"})
                payload = _read_json(self)
                preset_name = payload.get("preset", "")
                if preset_name not in VIDEO_PRESETS:
                    return _json_response(self, 400, {"error": "invalid preset"})
                result = _apply_video_preset(preset_name)
                state.update({"videoPreset": preset_name})
                _save_state(state)
                return _json_response(self, 200, {"ok": True, **result})

            return _json_response(self, 404, {"error": "not found"})
        except Exception as error:
            return _json_response(self, 500, {"error": str(error)})


if __name__ == "__main__":
    DEFAULT_RECORD_DIR.mkdir(parents=True, exist_ok=True)
    if not STATE_PATH.exists():
        _save_state({
            "recording": False,
            "recordPath": "",
            "recordDir": str(DEFAULT_RECORD_DIR),
            "recordStream": "",
            "videoPreset": "ultra",
        })
    ThreadingHTTPServer(("0.0.0.0", 8080), CameraHandler).serve_forever()
