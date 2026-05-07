# Claude Project Context

## Project Type

This is a Luckfox Pico / Rockchip RV1106 Linux IPC camera SDK tree plus a local Windows camera dashboard. Treat it as an embedded camera firmware project, not as a normal single-language application.

The current root is `E:\code\rvtest`. It has no `.git` directory in this checkout.

## What The System Is

The SDK builds a complete RV1106 camera device stack:

- boot firmware and Linux system image
- media libraries and camera pipeline
- `rkipc` camera application
- optional factory IPC web UI/backend
- local Windows web dashboard for preview, recording, and board-side quality control

## Chip / Board

Primary chip: Rockchip `rv1106`.

Evidence in the tree:

- `project/cfg/BoardConfig_IPC/BoardConfig-EMMC-Buildroot-RV1106_Luckfox_Pico_Ultra-IPC.mk`
- `RK_CHIP=rv1106`
- `RK_APP_TYPE=RKIPC_RV1106`
- `RK_ARCH=arm`
- `RK_TOOLCHAIN_CROSS=arm-rockchip830-linux-uclibcgnueabihf`
- board DTS example: `rv1106g-luckfox-pico-ultra.dts`

The tree also contains RV1103/RV1126/RK3588 variants, but do not confuse those with the active RV1106 IPC path.

## Important Directories

| Path | Meaning |
| --- | --- |
| `project/build.sh` | Top-level SDK build orchestrator. |
| `project/cfg/BoardConfig_IPC/` | Board configs for Luckfox Pico RV1103/RV1106 IPC products. |
| `sysdrv/` | U-Boot, kernel, rootfs, drivers, filesystem image tools. |
| `media/` | Rockchip camera/media stack: ISP, RKAIQ, MPP, RGA, IVE/IVA, audio, samples. |
| `project/app/rkipc/` | Main board-side IPC camera app. Most runtime camera behavior lives here. |
| `project/app/ipcweb/` | Factory IPC web backend/frontend, REST API, Nginx, HTTP-FLV delivery. |
| `tools/` | Linux/Windows flashing, upgrade, packing, and toolchain assets. |
| `web/rv1106_camera_dashboard/` | Local Windows dashboard using Python + MediaMTX. |

## 主要运行链路

```mermaid
flowchart TD
  subgraph Board["RV1106 板端"]
    Sensor["摄像头 Sensor\nMIPI CSI"]
    IQ["IQ 文件\n/oem/usr/share/iqfiles"]
    Ini["运行配置\n/userdata/rkipc.ini"]
    RKIPC["rkipc 主进程"]
    Init["初始化\n网络 / 系统 / ISP / RK_MPI / 视频 / 音频 / 存储"]
    ISP["RKAIQ / ISP"]
    VI["VI 采集"]
    VPSS["VPSS\n缩放 / 旋转 / 多路输出"]
    MainVenc["主码流 VENC0\nH.264/H.265"]
    SubVenc["子码流 VENC1\nH.264/H.265"]
    JPEG["JPEG 抓图"]
    OSD["OSD / ROI / 移动检测 / IVA/NPU"]
    RTSP["RTSP :554\n/live/0 /live/1"]
    RTMP["RTMP :1935\nmainstream / substream"]
    Storage["本地存储\n录像 / 抓图"]
    Socket["rkipc socket server\n参数控制"]
  end

  subgraph FactoryWeb["板端原厂 Web"]
    Nginx["Nginx :80"]
    Backend["ipcweb-backend\nREST / CGI"]
    WebUI["www-rkipc\nwxplayer.js"]
    HTTPFLV["HTTP-FLV\n/live?port=1935&app=live&stream=..."]
  end

  subgraph LocalWeb["Windows 本机监控台"]
    Start["start_camera_site.cmd"]
    MediaMTX["MediaMTX\nRTSP 转 WebRTC/HLS"]
    Server["camera_site_server.py :8080\n状态 / 录制 / 画质 API"]
    Browser["浏览器\nindex.html"]
    WebRTC["WebRTC :8889"]
    HLS["HLS :8888"]
    Playback["历史回放 :9996"]
    Records["recordings/"]
    State["recording_state.json"]
    ADB["ADB :5555\n修改配置并重启 rkipc"]
  end

  Ini --> RKIPC
  IQ --> ISP
  RKIPC --> Init
  Init --> ISP
  Sensor --> ISP --> VI --> VPSS
  VPSS --> MainVenc
  VPSS --> SubVenc
  VPSS --> JPEG
  VPSS --> OSD
  OSD --> MainVenc
  OSD --> SubVenc
  MainVenc --> RTSP
  SubVenc --> RTSP
  MainVenc --> RTMP
  SubVenc --> RTMP
  MainVenc --> Storage
  SubVenc --> Storage
  JPEG --> Storage
  RKIPC --> Socket

  RTMP --> Nginx
  Nginx --> HTTPFLV
  Nginx --> WebUI
  Nginx --> Backend
  Backend --> Socket
  WebUI --> HTTPFLV

  Start --> MediaMTX
  Start --> Server
  RTSP --> MediaMTX
  MediaMTX --> WebRTC
  MediaMTX --> HLS
  MediaMTX --> Playback
  MediaMTX --> Records
  WebRTC --> Browser
  HLS --> Browser
  Playback --> Browser
  Server --> Browser
  Server --> State
  Server --> Records
  Server --> MediaMTX
  Server --> ADB
  ADB --> Ini
```

## What The Local Dashboard Does

`web/rv1106_camera_dashboard` is a Windows-side helper app:

- `mediamtx.exe` pulls board RTSP:
  - `rtsp://192.168.31.18/live/0`
  - `rtsp://192.168.31.18/live/1`
- MediaMTX exposes browser-friendly streams:
  - WebRTC: `http://localhost:8889/main`, `http://localhost:8889/sub`
  - HLS: `http://localhost:8888/main`, `http://localhost:8888/sub`
- `camera_site_server.py` serves `index.html` and JSON APIs on port `8080`.
- Recording state is stored in `recording_state.json`.
- Recordings go under `recordings/`.
- Quality presets are applied by ADB: edit `/userdata/rkipc.ini`, push it back, and restart `/oem/usr/bin/rkipc`.

Start it with:

```powershell
E:\code\rvtest\web\rv1106_camera_dashboard\start_camera_site.cmd
```

Then open:

```text
http://localhost:8080/index.html
```

Stop it with:

```powershell
E:\code\rvtest\web\rv1106_camera_dashboard\stop_camera_site.cmd
```

## Build Notes

Use Linux/Ubuntu or WSL2/Linux for SDK builds. Do not assume the full SDK can be built directly from Windows PowerShell.

Common SDK commands:

```bash
cd project
./build.sh lunch
./build.sh info
./build.sh media
./build.sh app
./build.sh sysdrv
./build.sh firmware
./build.sh allsave
```

构建链路如下：

```mermaid
flowchart TD
  Config["板级配置\nBoardConfig_IPC/*.mk\nRK_CHIP=rv1106"]
  Build["统一构建入口\nproject/build.sh"]
  Toolchain["交叉工具链\narm-rockchip830-linux-uclibcgnueabihf"]
  Sysdrv["系统层 sysdrv\nU-Boot / Kernel / rootfs / 驱动"]
  Media["媒体层 media\nISP / RKAIQ / MPP / RGA / samples"]
  App["应用层 project/app\nrkipc / ipcweb / wifi_app"]
  Overlay["板级 overlay\n/oem / userdata / init scripts / iqfiles"]
  Image["镜像打包\nboot.img / rootfs.img / oem.img"]
  Firmware["固件产物\noutput/image"]

  Config --> Build
  Toolchain --> Sysdrv
  Toolchain --> Media
  Toolchain --> App
  Build --> Sysdrv
  Build --> Media
  Build --> App
  Build --> Overlay
  Sysdrv --> Image
  Media --> Image
  App --> Image
  Overlay --> Image
  Image --> Firmware
```

## Where To Modify

- Camera capture, encoding, RTSP/RTMP, OSD, ROI, IVA/NPU:
  `project/app/rkipc/rkipc/src/rv1106_ipc/`
- Shared RKIPC modules:
  `project/app/rkipc/rkipc/common/`
- Factory web API:
  `project/app/ipcweb/ipcweb-backend/src/`
- Factory web static assets:
  `project/app/ipcweb/ipcweb-backend/www-rkipc/`
- Local Windows dashboard:
  `web/rv1106_camera_dashboard/index.html`
  `web/rv1106_camera_dashboard/camera_site_server.py`
  `web/rv1106_camera_dashboard/mediamtx.yml`

## Cautions For Future Agents

- Preserve vendor binaries, toolchains, prebuilt libraries, and firmware assets unless the task explicitly requires changing them.
- Be careful with Chinese text encoding. Some existing docs display mojibake in PowerShell output.
- Browser playback generally requires H.264; stock RV1106 ini examples may use H.265.
- If changing board runtime config, remember that `/userdata/rkipc.ini` is the writable runtime config used by `rkipc`.
- The current Windows dashboard hardcodes:
  - device IP: `192.168.31.18`
  - ADB serial: `192.168.31.18:5555`
  - ADB path: `E:\dev\ADB\platform-tools\adb.exe`
  - site port: `8080`
  - WebRTC port: `8889`
  - HLS port: `8888`
  - MediaMTX API: `127.0.0.1:9997`
- Current checkout has no Git metadata, so verify edits by reading files directly.
