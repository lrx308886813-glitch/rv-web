# 云端上传清单

## 已纳入

| 路径 | 用途 |
| --- | --- |
| `README.md` | 云端副本说明。 |
| `.gitignore` | 防止误提交录像、日志、大二进制、厂商 SDK。 |
| `agent.md` | 项目结构和架构说明。 |
| `claude.md` | 给云端 Agent / Claude 使用的项目上下文。 |
| `PROJECT_READING_GUIDE.md` | 第一次拿到工程的阅读流程。 |
| `web/rv1106_camera_dashboard/camera_site_server.py` | 本机 Python API，负责状态、录制、画质切换和 ADB 控制。 |
| `web/rv1106_camera_dashboard/index.html` | 浏览器控制台页面。 |
| `web/rv1106_camera_dashboard/mediamtx.yml` | MediaMTX 转流配置。 |
| `web/rv1106_camera_dashboard/start_camera_site.*` | Windows 启动脚本。 |
| `web/rv1106_camera_dashboard/stop_camera_site.*` | Windows 停止脚本。 |
| `web/rv1106_camera_dashboard/操作指南.md` | 本机使用说明。 |
| `web/rv1106_camera_dashboard/LICENSE` | MediaMTX 相关 MIT License 文本。 |

## 已排除

| 路径或类型 | 原因 |
| --- | --- |
| `media/` | Rockchip/Luckfox 媒体 SDK 和预编译库，体积大且授权边界复杂。 |
| `project/` | 厂商工程层和板级配置，暂不上传。 |
| `sysdrv/` | Linux kernel、U-Boot、rootfs、驱动，体积大。 |
| `tools/` | 工具链、烧录工具和升级工具，体积大。 |
| `output/` | 构建产物。 |
| `recordings/` | 本机录像。 |
| `*.log` | 运行日志。 |
| `mediamtx.exe` | 大二进制，可从 MediaMTX 官方发布包恢复。 |

## 下一步

1. 确认云端仓库目标。
2. 初始化 Git。
3. 首次提交。
4. 推送到私有仓库。

不要在没有明确授权的情况下上传完整 Rockchip/Luckfox SDK。
