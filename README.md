# RM-01 CFe-B存储卡制作工具 / RM-01 CFe-B Card Maker Tool

[English](#english) | [中文](#中文)

---

<a name="english"></a>
## English

### Description

A comprehensive Linux-based tool for creating RM-01 CFe-B storage cards with automated LLM model deployment, backend configuration, and optimization settings. Supports multiple model manufacturers and platforms (Orin/Thor) with progress tracking and intelligent auto-detection.

### Features

1. **System Settings**
   - Display storage devices using `lsblk`
   - Scan and parse models from `Models_download` folder
   - Auto-detect manufacturer and model names
   - Save configuration to `config.json` for persistence

2. **Create Model Card**
   - Check three partitions on `/dev/sda` (rm01rootfs, rm01models, rm01app)
   - Backend selection:
     - FlashAttention: Copy Attention folder to `/dev/sda1/home/rm01/autoShell`
     - FlashInfer: Copy Infer folder to `/dev/sda1/home/rm01/autoShell`
     - Auto-detect: Automatically select backend based on model from `backend_list.yaml`
   - Model manufacturer selection (Qwen/GPT/Llama/DeepSeek/Gemma/Others)
   - Model selection and deployment
   - Copy models to `/dev/sda2/llm` with progress bar
   - Optional dev mode configuration file generation (VRAM: 32G/48G/64G/128G)

3. **Add Model Optimization Config**
   - Automatically scan existing models in `/dev/sda2/llm/`
   - Select VRAM size (32G/48G/64G/128G)
   - Automatically add optimization and inference acceleration configuration files for all detected models

### Installation

```bash
pip install -r requirements.txt
```

### Usage

#### Method 1: Direct Python execution
```bash
python3 main.py
```

#### Method 2: Using startup script
```bash
./run.sh
```

### Workflow

1. **First-time Setup**: Select "1. System Settings"
   - Program displays `lsblk` output to help locate disk devices
   - Enter disk path (e.g., `/dev/sdb` or `/mnt/usb`)
   - Program automatically scans `Models_download` folder and parses model list
   - Configuration saved to `config.json` for future use

2. **Create Model Card**: Select "2. Create Model Card"
   - Program checks three partitions on `/dev/sda`
   - Select backend type (1/2/3)
   - Select model manufacturer (1-6)
   - Select specific model
   - Program automatically copies files with progress display
   - Optionally generate dev mode configuration files

3. **Add Model Optimization Config**: Select "3. Add Model Optimization Config"
   - Program automatically scans existing models in `/dev/sda2/llm/`
   - Select VRAM size (1-4)
   - Program automatically adds optimization configuration files for all detected models

### Requirements

- Linux operating system
- Python 3.6+
- Root permissions (recommended) for accessing `/dev/sda` device
- Ensure `/dev/sda1` and `/dev/sda2` are properly mounted

### Directory Structure

The source disk should contain:
```
Disk Root/
├── Models_download/           # Model storage directory
│   ├── Manufacturer_Model/    # Format: Manufacturer_ModelName
│   └── ...
├── 98autoshell/              # Backend scripts directory
│   ├── Attention/            # FlashAttention backend
│   ├── Infer/                # FlashInfer backend
│   └── backend_list.yaml    # Backend configuration file
├── Model_dev_yaml/           # Dev mode configuration files
│   ├── 32G/
│   ├── 48G/
│   ├── 64G/
│   └── 128G/
└── fused_moe/                # Optimization configuration files
    ├── Orin/                 # For 32G/48G/64G VRAM
    └── Thor/                 # For 128G VRAM
```

### Notes

- Model folder naming: The program automatically recognizes manufacturer names (Qwen, GPT, Llama, DeepSeek, Gemma, etc.) from folder names. Examples:
  - `Qwen3-VL-8B-Instruct-FP8-Static` → Manufacturer: Qwen, Model: 3-VL-8B-Instruct-FP8-Static
  - `Qwen_ChatGLM-7B` → Manufacturer: Qwen, Model: ChatGLM-7B
  - Folders can use underscore (`_`) or hyphen (`-`) as separators, or just start with manufacturer name
- For auto-detection mode, ensure `/dev/sda2/98autoshell/backend_list.yaml` exists
- Configuration file saved in `config.json` in program directory
- Program automatically unmounts `/dev/sda` partitions on exit

---

<a name="中文"></a>
## 中文

### 简介

一个功能完整的Linux工具，用于制作RM-01 CFe-B存储卡，支持自动化LLM模型部署、后端配置和优化设置。支持多种模型厂商和平台（Orin/Thor），提供进度跟踪和智能自动检测功能。

### 主要功能

1. **系统设置**
   - 使用`lsblk`显示存储设备列表
   - 扫描并解析`Models_download`文件夹中的模型
   - 自动识别厂商和模型名称
   - 保存配置到`config.json`文件（持久化）

2. **制作模型卡**
   - 检查`/dev/sda`下的三个分区（rm01rootfs, rm01models, rm01app）
   - 后端类型选择：
     - FlashAttention：拷贝Attention文件夹到`/dev/sda1/home/rm01/autoShell`
     - FlashInfer：拷贝Infer文件夹到`/dev/sda1/home/rm01/autoShell`
     - 自动适配：根据选择的模型，从`backend_list.yaml`中自动查找对应的后端
   - 模型厂商选择（Qwen/GPT/Llama/DeepSeek/Gemma/Others）
   - 模型选择和部署
   - 拷贝模型到`/dev/sda2/llm`（带进度条显示）
   - 可选生成dev模式配置文件（显存大小：32G/48G/64G/128G）

3. **添加模型优化与推理加速配置文件**
   - 自动扫描`/dev/sda2/llm/`下已存在的模型文件夹
   - 选择显存大小（32G/48G/64G/128G）
   - 自动为所有检测到的模型添加优化与推理加速配置文件

### 安装依赖

```bash
pip install -r requirements.txt
```

### 使用方法

#### 方法1：直接运行Python脚本
```bash
python3 main.py
```

#### 方法2：使用启动脚本
```bash
./run.sh
```

### 使用流程

1. **首次使用**：选择"1. 系统设置"
   - 程序会显示`lsblk`输出，帮助您找到硬盘设备
   - 输入硬盘地址（例如：`/dev/sdb` 或 `/mnt/usb`）
   - 程序会自动扫描`Models_download`文件夹并解析模型列表
   - 配置会保存到`config.json`，下次启动无需重新设置

2. **制作模型卡**：选择"2. 制作模型卡"
   - 程序会检查`/dev/sda`下的三个分区
   - 选择后端类型（1/2/3）
   - 选择模型厂商（1-6）
   - 选择具体模型
   - 程序会自动拷贝文件并显示进度
   - 可选择是否生成dev模式配置文件

3. **添加模型优化与推理加速配置文件**：选择"3. 添加模型优化与推理加速配置文件"
   - 程序自动扫描`/dev/sda2/llm/`下已存在的模型文件夹
   - 选择显存大小（1-4）
   - 程序自动为所有检测到的模型添加优化配置文件

### 系统要求

- Linux操作系统
- Python 3.6+
- Root权限（推荐）用于访问`/dev/sda`设备
- 请确保`/dev/sda1`和`/dev/sda2`已正确挂载

### 目录结构

源硬盘应包含以下目录结构：
```
硬盘根目录/
├── Models_download/           # 模型存储目录
│   ├── 厂商_模型名/            # 格式：厂商_模型名
│   └── ...
├── 98autoshell/               # 后端脚本目录
│   ├── Attention/             # FlashAttention后端
│   ├── Infer/                 # FlashInfer后端
│   └── backend_list.yaml      # 后端配置文件
├── Model_dev_yaml/            # Dev模式配置文件
│   ├── 32G/
│   ├── 48G/
│   ├── 64G/
│   └── 128G/
└── fused_moe/                 # 优化配置文件
    ├── Orin/                  # 用于32G/48G/64G显存
    └── Thor/                  # 用于128G显存
```

### 注意事项

- 模型文件夹命名：程序会自动识别文件夹名中的厂商名称（Qwen、GPT、Llama、DeepSeek、Gemma等）。示例：
  - `Qwen3-VL-8B-Instruct-FP8-Static` → 厂商：Qwen，模型：3-VL-8B-Instruct-FP8-Static
  - `Qwen_ChatGLM-7B` → 厂商：Qwen，模型：ChatGLM-7B
  - 文件夹可以使用下划线（`_`）或连字符（`-`）作为分隔符，或者直接以厂商名开头
- 如果选择自动适配，需要确保`/dev/sda2/98autoshell/backend_list.yaml`文件存在
- 配置文件保存在程序目录下的`config.json`文件中
- 程序退出时会自动卸载`/dev/sda`分区

### 许可证

本项目采用 Apache2.0 许可证。
