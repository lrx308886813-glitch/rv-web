# RV1106 Camera Dashboard Cloud Copy

这是 `E:\code\rvtest` 工程的云端精简副本，目标是让 Codex / Git 仓库只携带可维护的自写部分和项目说明，不上传 Rockchip/Luckfox SDK 全量源码、工具链、预编译库、录像文件和运行日志。

## 这个副本包含什么

```text
agent.md
claude.md
PROJECT_READING_GUIDE.md
web/rv1106_camera_dashboard/
```

`web/rv1106_camera_dashboard` 包含：

```text
camera_site_server.py
index.html
mediamtx.yml
start_camera_site.cmd
start_camera_site.ps1
stop_camera_site.cmd
stop_camera_site.ps1
操作指南.md
LICENSE
```

## 这个副本不包含什么

为避免把厂商 SDK、二进制、录像和日志上传到云端，以下内容没有复制：

```text
media/
project/
sysdrv/
tools/
output/
web/rv1106_camera_dashboard/recordings/
web/rv1106_camera_dashboard/*.log
web/rv1106_camera_dashboard/mediamtx.exe
```

## 本机恢复运行方式

这个云端副本不包含 `mediamtx.exe`。如果要在 Windows 本机直接运行，需要把 MediaMTX Windows amd64 可执行文件放回：

```text
web/rv1106_camera_dashboard/mediamtx.exe
```

然后运行：

```powershell
web\rv1106_camera_dashboard\start_camera_site.cmd
```

打开：

```text
http://localhost:8080/index.html
```

## 设备侧默认假设

当前 Web 工具默认连接：

```text
RV1106 IP: 192.168.31.18
RTSP main: rtsp://192.168.31.18/live/0
RTSP sub : rtsp://192.168.31.18/live/1
ADB      : 192.168.31.18:5555
ADB path : E:\dev\ADB\platform-tools\adb.exe
```

如果设备 IP 或 ADB 路径变化，需要改：

```text
web/rv1106_camera_dashboard/camera_site_server.py
web/rv1106_camera_dashboard/mediamtx.yml
```

## 为什么不上传完整 SDK

完整工程包含：

- Rockchip/Luckfox SDK 大量源码和板级文件
- Linux kernel / U-Boot / Buildroot
- 交叉工具链
- 厂商预编译库
- Windows 烧录工具
- 本机录像和运行日志

这些内容体积大、授权边界复杂，也不适合直接放到云端代码仓库。若未来确实需要云端完整编译，应单独确认厂商 SDK 授权和仓库访问范围。
