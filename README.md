# RM-01 CFe-B存储卡制作工具 / RM-01 CFe-B Card Maker Tool

[English](#english) | [中文](#中文)

---

<a name="english"></a>
## English

### Description

A comprehensive Linux-based tool for creating RM-01 CFe-B storage cards with automated LLM model deployment, backend configuration, RAG model setup, and optimization settings. Supports multiple model manufacturers and platforms (Orin/Thor) with progress tracking and intelligent auto-detection.

### Features

1. **System Settings**
   - **Model Master Disk Confirmation**: Automatically scan all connected disks to find the disk labeled "RMinte_Models"
   - **Target CFe-B Card Confirmation**: Automatically detect and verify the target CFe-B card (the CF card inserted into RM-01)
   - Scan and parse models from `Models_download` or `Models_Download` folder (case-insensitive)
   - Auto-detect manufacturer and model names
   - Save configuration to `config.json` for persistence

2. **Create Model Card**
   - Automatically copy `auto` and `dev` folders from master disk's `tree` folder
   - Backend selection:
     - FlashAttention: Copy Attention folder to target CFe-B card's rootfs partition
     - FlashInfer: Copy Infer folder to target CFe-B card's rootfs partition
     - Auto-detect: Automatically select backend based on model from `backend_list.yaml` (read from master disk)
   - Model manufacturer selection (Qwen/GPT/Llama/DeepSeek/Gemma/ZhipuAI/Baichuan/InternLM/Others)
   - Model selection and deployment
   - Copy models to `rm01models/dev/llm/` with progress bar
   - Copy `backend_list.yaml` to target CFe-B card automatically
   - Optional dev mode configuration file generation (VRAM: 32G/48G/64G/128G)
   - Copy `llm_run.yaml` to `rm01models/dev/llm/` directory

3. **Add Model Optimization Config**
   - Automatically scan existing models in `rm01models/dev/llm/`
   - Select VRAM size (32G/48G/64G/128G)
   - Automatically add optimization and inference acceleration configuration files for all detected models

4. **RAG Model Configuration**
   - **Add Embedding Model**: Scan and copy embedding models from `Models_download/embedding` folder
   - **Add Reranker Model**: Scan and copy reranker models from `Models_download/reranker` folder
   - Automatically detect models containing "Embedding" or "Rerank/Reranker" keywords
   - Copy models to `rm01models/dev/embedding/` or `rm01models/dev/reranker/`
   - Optional automatic configuration file generation (`embedding_run.yaml` or `reranker_run.yaml`)

5. **Set Full Disk Permissions**
   - Set permissions (`chmod 755 -R`) and ownership (`chown -R rm01:rm01`) for:
     - `rm01rootfs/home/rm01/autoShell` directory
     - `rm01models` partition
   - Requires root permissions

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

**Note**: It is recommended to run with root permissions:
```bash
sudo python3 main.py
```

### Workflow

1. **First-time Setup**: Select "1. System Settings"
   - **Model Master Disk Confirmation**: Program automatically scans all disks and finds the disk labeled "RMinte_Models"
   - **Target CFe-B Card Confirmation**: Program automatically detects the target CFe-B card with three partitions (rootfs, models, app)
   - Program automatically scans `Models_download` or `Models_Download` folder and parses model list
   - Configuration saved to `config.json` for future use

2. **Create Model Card**: Select "2. Create Model Card"
   - Program automatically copies `auto` and `dev` folders from master disk
   - Select backend type (1: FlashAttention, 2: FlashInfer, 3: Auto-detect)
   - Select model manufacturer
   - Select specific model
   - Program automatically copies files with progress display
   - Optionally generate dev mode configuration files
   - Models are copied to `rm01models/dev/llm/模型名称/`

3. **Add Model Optimization Config**: Select "3. Add Model Optimization Config"
   - Program automatically scans existing models in `rm01models/dev/llm/`
   - Select VRAM size (1-4)
   - Program automatically adds optimization configuration files for all detected models

4. **RAG Model Configuration**: Select "4. RAG Model Configuration"
   - Choose to add Embedding or Reranker model
   - Select from available models
   - Models are copied to corresponding directories
   - Optionally generate automatic configuration files

5. **Set Full Disk Permissions**: Select "5. Set Full Disk Permissions"
   - Set permissions and ownership for autoShell and models partition
   - Requires root permissions

### Requirements

- Linux operating system
- Python 3.6+
- Root permissions (recommended) for file operations
- Ensure target CFe-B card partitions are properly mounted

### Directory Structure

**Master Disk Structure:**
```
Master Disk Root/
├── Models_download/           # Model storage directory (or Models_Download)
│   ├── Manufacturer_Model/    # Format: Manufacturer_ModelName
│   ├── embedding/             # Embedding models
│   │   └── ModelName_Embedding/
│   └── reranker/             # Reranker models
│       └── ModelName_Reranker/
├── tree/                     # Template folder
│   ├── auto/                 # Auto folder template
│   └── dev/                  # Dev folder template
│       ├── embedding/        # Embedding directory template
│       ├── reranker/         # Reranker directory template
│       └── llm/              # LLM directory template
├── 98autoshell/              # Backend scripts directory
│   ├── Attention/            # FlashAttention backend
│   ├── Infer/                # FlashInfer backend
│   └── backend_list.yaml    # Backend configuration file
├── Model_dev_yaml/           # Dev mode configuration files
│   ├── 32G/
│   ├── 48G/
│   ├── 64G/
│   ├── 128G/
│   ├── embedding/            # Embedding model configs
│   └── reranker/             # Reranker model configs
└── fused_moe/                # Optimization configuration files
    ├── Orin/                 # For 32G/48G/64G VRAM
    └── Thor/                 # For 128G VRAM
```

**Target CFe-B Card Structure:**
```
rm01rootfs/                   # Rootfs partition
└── home/rm01/autoShell/      # Backend files (Attention or Infer)

rm01models/                    # Models partition
├── auto/                      # Auto folder
└── dev/                       # Dev folder
    ├── llm/                   # LLM models
    │   ├── ModelName/         # Model folders
    │   └── llm_run.yaml       # LLM configuration file
    ├── embedding/             # Embedding models
    │   ├── ModelName/
    │   └── embedding_run.yaml
    └── reranker/              # Reranker models
        ├── ModelName/
        └── reranker_run.yaml

rm01app/                       # App partition
```

### Notes

- Model folder naming: The program automatically recognizes manufacturer names (Qwen, GPT, Llama, DeepSeek, Gemma, ChatGLM, Baichuan, InternLM) from folder names
- The program supports both `Models_download` and `Models_Download` folder names (case-insensitive)
- For auto-detection mode, `backend_list.yaml` is read from the master disk's `98autoshell` folder
- Configuration file saved in `config.json` in program directory
- When copying `dev` folder, the program preserves existing models in `dev/llm/` directory
- All file operations support overwrite mode (existing files/folders will be replaced)

---

<a name="中文"></a>
## 中文

### 简介

一个功能完整的Linux工具，用于制作RM-01 CFe-B存储卡，支持自动化LLM模型部署、后端配置、RAG模型设置和优化设置。支持多种模型厂商和平台（Orin/Thor），提供进度跟踪和智能自动检测功能。

### 主要功能

1. **系统设置**
   - **模型母版磁盘确认**：自动扫描所有连接的磁盘，查找标签为"RMinte_Models"的磁盘
   - **目标CFe-B卡确认**：自动检测并验证目标CFe-B卡（插入RM-01的CF卡）
   - 扫描并解析`Models_download`或`Models_Download`文件夹中的模型（支持大小写）
   - 自动识别厂商和模型名称
   - 保存配置到`config.json`文件（持久化）

2. **制作模型卡**
   - 自动从母版卡的`tree`文件夹拷贝`auto`和`dev`文件夹
   - 后端类型选择：
     - FlashAttention：拷贝Attention文件夹到目标CFe-B卡的rootfs分区
     - FlashInfer：拷贝Infer文件夹到目标CFe-B卡的rootfs分区
     - 自动适配：根据选择的模型，从母版卡的`backend_list.yaml`中自动查找对应的后端
   - 模型厂商选择（Qwen/GPT/Llama/DeepSeek/Gemma/ZhipuAI/Baichuan/InternLM/其他）
   - 模型选择和部署
   - 拷贝模型到`rm01models/dev/llm/`（带进度条显示）
   - 自动拷贝`backend_list.yaml`到目标CFe-B卡
   - 可选生成dev模式配置文件（显存大小：32G/48G/64G/128G）
   - 拷贝`llm_run.yaml`到`rm01models/dev/llm/`目录

3. **添加模型优化与推理加速配置文件**
   - 自动扫描`rm01models/dev/llm/`下已存在的模型文件夹
   - 选择显存大小（32G/48G/64G/128G）
   - 自动为所有检测到的模型添加优化与推理加速配置文件

4. **制作与配置RAG模型**
   - **添加Embedding模型**：扫描并拷贝`Models_download/embedding`文件夹中的embedding模型
   - **添加Reranker模型**：扫描并拷贝`Models_download/reranker`文件夹中的reranker模型
   - 自动检测包含"Embedding"或"Rerank/Reranker"关键词的模型
   - 拷贝模型到`rm01models/dev/embedding/`或`rm01models/dev/reranker/`
   - 可选生成自动拉起配置文件（`embedding_run.yaml`或`reranker_run.yaml`）

5. **全盘加权**
   - 为以下路径设置权限（`chmod 755 -R`）和所有者（`chown -R rm01:rm01`）：
     - `rm01rootfs/home/rm01/autoShell`目录
     - `rm01models`分区
   - 需要root权限

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

**注意**：建议使用root权限运行：
```bash
sudo python3 main.py
```

### 使用流程

1. **首次使用**：选择"1. 系统设置"
   - **模型母版磁盘确认**：程序自动扫描所有磁盘，查找标签为"RMinte_Models"的磁盘
   - **目标CFe-B卡确认**：程序自动检测具有三个分区（rootfs、models、app）的目标CFe-B卡
   - 程序会自动扫描`Models_download`或`Models_Download`文件夹并解析模型列表
   - 配置会保存到`config.json`，下次启动无需重新设置

2. **制作模型卡**：选择"2. 制作模型卡"
   - 程序自动从母版卡拷贝`auto`和`dev`文件夹
   - 选择后端类型（1：FlashAttention，2：FlashInfer，3：自动适配）
   - 选择模型厂商
   - 选择具体模型
   - 程序会自动拷贝文件并显示进度
   - 可选择是否生成dev模式配置文件
   - 模型被拷贝到`rm01models/dev/llm/模型名称/`

3. **添加模型优化与推理加速配置文件**：选择"3. 添加模型优化与推理加速配置文件"
   - 程序自动扫描`rm01models/dev/llm/`下已存在的模型文件夹
   - 选择显存大小（1-4）
   - 程序自动为所有检测到的模型添加优化配置文件

4. **制作与配置RAG模型**：选择"4. 制作与配置RAG模型"
   - 选择添加Embedding或Reranker模型
   - 从可用模型中选择
   - 模型被拷贝到相应目录
   - 可选择生成自动拉起配置文件

5. **全盘加权**：选择"5. 全盘加权"
   - 为autoShell和models分区设置权限和所有者
   - 需要root权限

### 系统要求

- Linux操作系统
- Python 3.6+
- Root权限（推荐）用于文件操作
- 请确保目标CFe-B卡分区已正确挂载

### 目录结构

**母版卡目录结构：**
```
母版卡根目录/
├── Models_download/           # 模型存储目录（或Models_Download）
│   ├── 厂商_模型名/            # 格式：厂商_模型名
│   ├── embedding/             # Embedding模型目录
│   │   └── 模型名_Embedding/
│   └── reranker/             # Reranker模型目录
│       └── 模型名_Reranker/
├── tree/                     # 模板文件夹
│   ├── auto/                 # Auto文件夹模板
│   └── dev/                  # Dev文件夹模板
│       ├── embedding/        # Embedding目录模板
│       ├── reranker/         # Reranker目录模板
│       └── llm/              # LLM目录模板
├── 98autoshell/               # 后端脚本目录
│   ├── Attention/             # FlashAttention后端
│   ├── Infer/                 # FlashInfer后端
│   └── backend_list.yaml      # 后端配置文件
├── Model_dev_yaml/            # Dev模式配置文件
│   ├── 32G/
│   ├── 48G/
│   ├── 64G/
│   ├── 128G/
│   ├── embedding/             # Embedding模型配置
│   └── reranker/             # Reranker模型配置
└── fused_moe/                 # 优化配置文件
    ├── Orin/                  # 用于32G/48G/64G显存
    └── Thor/                  # 用于128G显存
```

**目标CFe-B卡目录结构：**
```
rm01rootfs/                   # Rootfs分区
└── home/rm01/autoShell/      # 后端文件（Attention或Infer）

rm01models/                    # Models分区
├── auto/                      # Auto文件夹
└── dev/                       # Dev文件夹
    ├── llm/                   # LLM模型
    │   ├── 模型名称/           # 模型文件夹
    │   └── llm_run.yaml       # LLM配置文件
    ├── embedding/             # Embedding模型
    │   ├── 模型名称/
    │   └── embedding_run.yaml
    └── reranker/              # Reranker模型
        ├── 模型名称/
        └── reranker_run.yaml

rm01app/                       # App分区
```

### 注意事项

- 模型文件夹命名：程序会自动识别文件夹名中的厂商名称（Qwen、GPT、Llama、DeepSeek、Gemma、ChatGLM、Baichuan、InternLM等）
- 程序支持`Models_download`和`Models_Download`两种文件夹名称（大小写不敏感）
- 如果选择自动适配模式，`backend_list.yaml`从母版卡的`98autoshell`文件夹读取
- 配置文件保存在程序目录下的`config.json`文件中
- 拷贝`dev`文件夹时，程序会保留`dev/llm/`目录中已存在的模型
- 所有文件操作支持覆盖模式（已存在的文件/文件夹会被替换）

### License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.

### 许可证

本项目采用 Apache License 2.0 许可证。详情请参阅 [LICENSE](LICENSE) 文件。
