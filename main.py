#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RM-01 CFe-B存储卡制作工具
"""

import os
import sys
import json
import shutil
import subprocess
import re
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from tqdm import tqdm

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')

# 支持的厂商列表
MANUFACTURERS = {
    '1': 'Qwen',
    '2': 'GPT',
    '3': 'Llama',
    '4': 'DeepSeek',
    '5': 'Gemma',
    '6': 'ZhipuAI',
    '7': 'Others'
}


def load_config() -> Dict:
    """加载配置文件"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"读取配置文件失败: {e}")
            return {}
    return {}


def save_config(config: Dict):
    """保存配置文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存配置文件失败: {e}")


def show_lsblk():
    """显示lsblk输出"""
    print("\n正在扫描存储设备...")
    try:
        result = subprocess.run(['lsblk'], capture_output=True, text=True, check=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"执行lsblk失败: {e}")
    except FileNotFoundError:
        print("错误: 未找到lsblk命令，请确保在Linux系统上运行")


def scan_models(base_path: str) -> List[Dict]:
    """扫描Models_download文件夹，解析模型列表"""
    models = []
    models_path = os.path.join(base_path, 'Models_download')
    
    if not os.path.exists(models_path):
        print(f"错误: 未找到Models_download文件夹: {models_path}")
        return models
    
    print(f"\n正在扫描模型文件夹: {models_path}")
    
    # 已知厂商列表（用于识别模型文件夹名中的厂商）
    known_manufacturers = ['Qwen', 'GPT', 'Llama', 'DeepSeek', 'Gemma', 'ChatGLM', 'Baichuan', 'InternLM']
    
    # 遍历Models_download下的所有文件夹
    for item in os.listdir(models_path):
        item_path = os.path.join(models_path, item)
        if os.path.isdir(item_path):
            manufacturer = None
            model_name = None
            
            # 方法0: 检查是否包含GLM，归类到ZhipuAI
            if 'GLM' in item.upper():
                manufacturer = 'ZhipuAI'
                model_name = item
            
            # 方法1: 检查是否以已知厂商开头
            if manufacturer is None:
                for mfg in known_manufacturers:
                    if item.startswith(mfg):
                        manufacturer = mfg
                        # 提取模型名：去掉厂商名和后面的分隔符（下划线或连字符）
                        remaining = item[len(mfg):].lstrip('_-')
                        model_name = remaining if remaining else item
                        break
            
            # 方法2: 如果没有匹配到已知厂商，尝试用分隔符分割
            if manufacturer is None:
                if '_' in item:
                    parts = item.split('_', 1)  # 使用下划线分割，最多分割一次
                elif '-' in item:
                    parts = item.split('-', 1)  # 使用连字符分割，最多分割一次
                else:
                    parts = None
                
                if parts and len(parts) >= 2:
                    manufacturer = parts[0]
                    model_name = parts[1]
                else:
                    # 如果都没有分隔符，整个作为模型名，厂商为Others
                    manufacturer = 'Others'
                    model_name = item
            
            models.append({
                'manufacturer': manufacturer,
                'model_name': model_name,
                'full_name': item,
                'path': item_path
            })
            print(f"  发现模型: {item}")
    
    return models


def find_rminte_models_disk() -> Optional[str]:
    """扫描所有磁盘，找到标签为RMinte_Models的磁盘"""
    print("\n正在扫描所有磁盘，查找标签为'RMinte_Models'的磁盘...")
    
    try:
        # 使用blkid查找标签
        result = subprocess.run(['blkid'], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        
        for line in lines:
            if 'LABEL="RMinte_Models"' in line or "LABEL='RMinte_Models'" in line:
                # 提取设备路径
                parts = line.split(':')
                if parts:
                    device = parts[0].strip()
                    # 获取挂载点
                    mount_point = get_mount_point(device)
                    if mount_point:
                        return mount_point
                    else:
                        # 如果没有挂载，返回设备路径
                        return device
        
        # 如果blkid没找到，尝试使用lsblk
        result = subprocess.run(['lsblk', '-o', 'NAME,LABEL,MOUNTPOINT'], 
                              capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        
        for line in lines[1:]:  # 跳过标题行
            if 'RMinte_Models' in line:
                parts = line.split()
                if len(parts) >= 3:
                    mount_point = parts[2]
                    if mount_point and mount_point != '/':
                        return mount_point
                    elif len(parts) >= 1:
                        device_name = parts[0]
                        # 构建完整设备路径
                        if device_name.startswith('/dev/'):
                            device = device_name
                        else:
                            device = f'/dev/{device_name}'
                        mount_point = get_mount_point(device)
                        if mount_point:
                            return mount_point
                        return device
        
        return None
    except subprocess.CalledProcessError as e:
        print(f"扫描磁盘失败: {e}")
        return None
    except FileNotFoundError:
        print("错误: 未找到blkid或lsblk命令")
        return None


def confirm_model_disk():
    """模型母版磁盘确认"""
    print("\n=== 模型母版磁盘确认 ===")
    
    disk_path = find_rminte_models_disk()
    
    if not disk_path:
        print("\n错误: 未找到标签为'RMinte_Models'的磁盘")
        print("请确保磁盘已连接并正确挂载")
        return
    
    print(f"\n✓ 找到模型母版磁盘: {disk_path}")
    
    # 检查路径是否存在
    if not os.path.exists(disk_path):
        print(f"错误: 路径不存在: {disk_path}")
        return
    
    # 扫描模型
    models = scan_models(disk_path)
    
    if not models:
        print("警告: 未找到任何模型")
        return
    
    # 保存配置
    config = load_config()
    config['disk_path'] = disk_path
    config['models'] = models
    save_config(config)
    
    print(f"\n✓ 设置已保存！共找到 {len(models)} 个模型")
    print("按回车键返回系统设置菜单...")
    input()


def check_cfeb_card_partitions(disk_device: str) -> bool:
    """检查CFe-B卡的分区和分区名
    
    Args:
        disk_device: 磁盘设备路径，如 /dev/sda
        
    Returns:
        bool: 检查是否通过
    """
    # 从磁盘设备路径提取基础名称（如 /dev/sda -> sda）
    disk_base = os.path.basename(disk_device)
    
    # 构建三个分区路径
    partitions = {
        'rootfs': f'{disk_device}1',
        'models': f'{disk_device}2',
        'app': f'{disk_device}3'
    }
    
    print(f"\n正在检查 {disk_device} 的分区...")
    
    # 检查分区是否存在
    missing_partitions = []
    for name, path in partitions.items():
        if not os.path.exists(path):
            missing_partitions.append((name, path))
            print(f"✗ {name}: {path} 不存在")
        else:
            print(f"✓ {name}: {path} 存在")
    
    if missing_partitions:
        print(f"\n错误: 缺少以下分区:")
        for name, path in missing_partitions:
            print(f"  - {name}: {path}")
        return False
    
    # 检查分区标签/名称
    print("\n正在检查分区标签...")
    try:
        result = subprocess.run(['blkid'], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        
        partition_labels = {}
        for line in lines:
            for name, path in partitions.items():
                if path in line:
                    # 提取LABEL
                    label_match = re.search(r'LABEL="([^"]+)"', line)
                    if label_match:
                        partition_labels[name] = label_match.group(1)
                    else:
                        # 尝试单引号
                        label_match = re.search(r"LABEL='([^']+)'", line)
                        if label_match:
                            partition_labels[name] = label_match.group(1)
        
        # 检查标签是否符合要求
        expected_labels = {
            'rootfs': 'rootfs',
            'models': 'models',
            'app': 'app'
        }
        
        label_errors = []
        for name, expected_label in expected_labels.items():
            actual_label = partition_labels.get(name, '')
            if actual_label != expected_label:
                label_errors.append((name, expected_label, actual_label))
                print(f"✗ {name}: 期望标签 '{expected_label}', 实际标签 '{actual_label}'")
            else:
                print(f"✓ {name}: 标签正确 '{actual_label}'")
        
        if label_errors:
            print(f"\n警告: 以下分区的标签不符合要求:")
            for name, expected, actual in label_errors:
                print(f"  - {name}: 期望 '{expected}', 实际 '{actual}'")
            # 标签不匹配也允许继续，只是警告
            print("将继续使用该磁盘...")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"检查分区标签失败: {e}")
        # 即使标签检查失败，如果分区存在也返回True
        return True
    except FileNotFoundError:
        print("警告: 未找到blkid命令，跳过标签检查")
        return True


def find_target_cfeb_card() -> Optional[str]:
    """扫描所有磁盘设备，找到符合要求的目标CFe-B卡
    
    Returns:
        Optional[str]: 找到的目标CFe-B卡设备路径，如 /dev/sdb，如果未找到返回None
    """
    print("\n正在扫描所有磁盘设备，查找目标CFe-B卡...")
    
    # 获取所有磁盘设备（sda, sdb, sdc等）
    disk_devices = []
    for i in range(ord('a'), ord('z') + 1):
        disk_name = f'/dev/sd{chr(i)}'
        if os.path.exists(disk_name):
            disk_devices.append(disk_name)
    
    if not disk_devices:
        print("未检测到任何磁盘设备")
        return None
    
    print(f"检测到 {len(disk_devices)} 个磁盘设备: {', '.join(disk_devices)}")
    
    # 检查每个磁盘
    try:
        result = subprocess.run(['blkid'], capture_output=True, text=True, check=True)
        blkid_lines = result.stdout.strip().split('\n')
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("错误: 无法执行blkid命令")
        return None
    
    # 检查每个磁盘
    for disk_device in disk_devices:
        # 检查是否有三个分区
        partitions = {
            'rootfs': f'{disk_device}1',
            'models': f'{disk_device}2',
            'app': f'{disk_device}3'
        }
        
        # 检查分区是否存在
        missing_partitions = []
        for name, path in partitions.items():
            if not os.path.exists(path):
                missing_partitions.append(name)
        
        if missing_partitions:
            continue  # 跳过没有三个分区的磁盘
        
        # 检查分区标签和挂载点
        partition_labels = {}
        partition_mounts = {}
        
        # 从blkid获取标签
        for line in blkid_lines:
            for name, path in partitions.items():
                if path in line:
                    label_match = re.search(r'LABEL="([^"]+)"', line)
                    if label_match:
                        partition_labels[name] = label_match.group(1)
                    else:
                        label_match = re.search(r"LABEL='([^']+)'", line)
                        if label_match:
                            partition_labels[name] = label_match.group(1)
        
        # 从挂载点获取信息（作为备用）
        for name, path in partitions.items():
            mount_point = get_mount_point(path)
            if mount_point:
                partition_mounts[name] = mount_point
        
        # 检查是否是模型母版盘（优先检查，如果确认是就跳过）
        models_label = partition_labels.get('models', '')
        models_mount = partition_mounts.get('models', '')
        if 'RMinte_Models' in models_label or 'RMinte_models' in models_label or 'RMinte_Models' in models_mount:
            print(f"跳过模型母版盘: {disk_device} (标签: {models_label}, 挂载点: {models_mount})")
            continue  # 跳过模型母版盘
        
        # 检查标签是否符合要求（支持多种格式）
        # 期望的标签关键词
        expected_keywords = {
            'rootfs': ['rootfs'],
            'models': ['models'],
            'app': ['app']
        }
        
        # 检查标签是否匹配（支持完全匹配或包含关键词）
        all_match = True
        for name, keywords in expected_keywords.items():
            actual_label = partition_labels.get(name, '').lower()
            actual_mount = partition_mounts.get(name, '').lower()
            
            # 检查标签或挂载点是否包含关键词
            label_match = any(keyword in actual_label for keyword in keywords)
            mount_match = any(keyword in actual_mount for keyword in keywords)
            
            if not (label_match or mount_match):
                all_match = False
                break
        
        if all_match:
            print(f"✓ 找到目标CFe-B卡: {disk_device}")
            return disk_device
    
    return None


def confirm_cfeb_card() -> bool:
    """目标CFe-B卡（即插入RM-01的CF卡）确认
    
    Returns:
        bool: True表示成功并需要返回主菜单，False表示继续留在系统设置菜单
    """
    print("\n=== 目标CFe-B卡（即插入RM-01的CF卡）确认 ===")
    
    # 显示lsblk
    show_lsblk()
    
    # 扫描所有磁盘，找到目标CFe-B卡
    disk_device = find_target_cfeb_card()
    
    if not disk_device:
        print("\n未找到完全对应的目标CFe-B卡")
        print("请检查硬件连接，确保目标CFe-B卡已正确插入（分区标签应为: rootfs, models, app）")
        print("按回车键返回系统设置菜单...")
        input()
        return False
    
    # 获取分区标签信息用于显示
    partitions = {
        'rootfs': f'{disk_device}1',
        'models': f'{disk_device}2',
        'app': f'{disk_device}3'
    }
    
    print("\n正在获取分区详细信息...")
    try:
        result = subprocess.run(['blkid'], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        
        partition_labels = {}
        for line in lines:
            for name, path in partitions.items():
                if path in line:
                    label_match = re.search(r'LABEL="([^"]+)"', line)
                    if label_match:
                        partition_labels[name] = label_match.group(1)
                    else:
                        label_match = re.search(r"LABEL='([^']+)'", line)
                        if label_match:
                            partition_labels[name] = label_match.group(1)
        
        # 验证通过，保存配置并显示信息
        print(f"\n✓ 检测成功！")
        print(f"目标CFe-B卡: {disk_device}")
        print("分区信息:")
        for name, path in partitions.items():
            label = partition_labels.get(name, '未知')
            print(f"  - {name}: {path} (标签: {label})")
        
        # 保存配置
        config = load_config()
        config['cfeb_card'] = disk_device
        config['target_partitions'] = partition_labels
        save_config(config)
        
        print(f"\n配置已保存")
        print("按回车键返回主菜单...")
        input()
        return True  # 返回True表示需要返回到主菜单
        
    except subprocess.CalledProcessError as e:
        print(f"获取分区信息失败: {e}")
        print("\n未找到完全对应的目标CFe-B卡")
        print("请检查硬件连接，确保目标CFe-B卡已正确插入")
        print("按回车键返回系统设置菜单...")
        input()
        return False
    except FileNotFoundError:
        print("错误: 未找到blkid命令，无法验证分区标签")
        print("\n未找到完全对应的目标CFe-B卡")
        print("请检查硬件连接，确保目标CFe-B卡已正确插入")
        print("按回车键返回系统设置菜单...")
        input()
        return False


def system_settings():
    """系统设置功能"""
    while True:
        print("\n=== 系统设置 ===")
        print()
        print("1. 模型母版磁盘确认")
        print()
        print("2. 目标CFe-B卡（即插入RM-01的CF卡）确认")
        print()
        print("3. 返回主菜单")
        
        choice = input("\n请选择功能 (1-3): ").strip()
        
        if choice == '1':
            confirm_model_disk()
        elif choice == '2':
            # 如果CFe-B卡确认成功，需要返回到主菜单
            if confirm_cfeb_card():
                return
        elif choice == '3':
            return
        else:
            print("无效的选项，请重新选择")


def check_partitions():
    """检查/dev/sda下的三个分区"""
    partitions = {
        'rm01rootfs': '/dev/sda1',
        'rm01models': '/dev/sda2',
        'rm01app': '/dev/sda3'
    }
    
    print("\n=== 检查分区 ===")
    for name, path in partitions.items():
        if os.path.exists(path):
            print(f"✓ {name}: {path} 存在")
        else:
            print(f"✗ {name}: {path} 不存在")
    
    return partitions


def get_mount_point(device: str) -> Optional[str]:
    """获取设备的挂载点"""
    try:
        result = subprocess.run(['findmnt', '-n', '-o', 'TARGET', device], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    
    # 尝试从/proc/mounts读取
    try:
        with open('/proc/mounts', 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2 and parts[0] == device:
                    return parts[1]
    except:
        pass
    
    return None


def copy_with_progress(src: str, dst: str, description: str = "复制"):
    """带进度条的文件/文件夹复制"""
    if os.path.isfile(src):
        # 单文件复制
        total_size = os.path.getsize(src)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst, \
             tqdm(total=total_size, unit='B', unit_scale=True, desc=description) as pbar:
            while True:
                chunk = fsrc.read(8192)
                if not chunk:
                    break
                fdst.write(chunk)
                pbar.update(len(chunk))
    else:
        # 文件夹复制
        files = []
        for root, dirs, filenames in os.walk(src):
            for filename in filenames:
                files.append(os.path.join(root, filename))
        
        if not files:
            # 空文件夹
            os.makedirs(dst, exist_ok=True)
            return
        
        total_size = sum(os.path.getsize(f) for f in files)
        
        # 确保目标目录存在
        os.makedirs(dst, exist_ok=True)
        
        with tqdm(total=total_size, unit='B', unit_scale=True, desc=description) as pbar:
            for src_file in files:
                rel_path = os.path.relpath(src_file, src)
                dst_file = os.path.join(dst, rel_path)
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                
                with open(src_file, 'rb') as fsrc, open(dst_file, 'wb') as fdst:
                    while True:
                        chunk = fsrc.read(8192)
                        if not chunk:
                            break
                        fdst.write(chunk)
                        pbar.update(len(chunk))


def get_target_cfeb_device() -> Optional[str]:
    """从配置中获取目标CFe-B卡设备路径"""
    config = load_config()
    # 优先使用target_cfeb_card，如果没有则使用cfeb_card
    return config.get('target_cfeb_card') or config.get('cfeb_card')


def copy_backend(backend_type: str, config: Dict):
    """拷贝后端文件"""
    disk_path = config.get('disk_path', '')
    if not disk_path:
        print("错误: 未设置硬盘路径，请先进行系统设置")
        print("\n按回车键返回主菜单...")
        input()
        return False
    
    # 确定源路径
    if backend_type == '1':  # FlashAttention
        src_path = os.path.join(disk_path, '98autoshell', 'Attention')
    elif backend_type == '2':  # FlashInfer
        src_path = os.path.join(disk_path, '98autoshell', 'Infer')
    else:
        print("错误: 无效的后端类型")
        print("\n按回车键返回主菜单...")
        input()
        return False
    
    if not os.path.exists(src_path):
        print(f"错误: 源路径不存在: {src_path}")
        print("\n按回车键返回主菜单...")
        input()
        return False
    
    # 获取目标CFe-B卡设备
    target_device = get_target_cfeb_device()
    if not target_device:
        print("错误: 未设置目标CFe-B卡，请先进行系统设置")
        print("\n按回车键返回主菜单...")
        input()
        return False
    
    # 获取目标CFe-B卡第一个分区的挂载点（rootfs分区）
    mount_point = get_mount_point(f'{target_device}1')
    if not mount_point:
        print(f"错误: {target_device}1未挂载，请先挂载该分区")
        print("\n按回车键返回主菜单...")
        input()
        return False
    
    # 检查挂载点是否可写
    if not os.access(mount_point, os.W_OK):
        print(f"\n错误: 权限不足，无法写入 {mount_point}")
        print("请使用 sudo 运行程序：sudo python3 main.py")
        print("\n按回车键返回主菜单...")
        input()
        return False
    
    # 目标路径：挂载点下的/home/rm01/autoShell
    dst_path = os.path.join(mount_point, 'home', 'rm01', 'autoShell')
    
    print(f"\n正在拷贝后端文件...")
    print(f"源: {src_path}")
    print(f"目标: {dst_path}")
    
    try:
        # 确保目标目录的父目录存在
        try:
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        except PermissionError:
            print(f"\n错误: 权限不足，无法创建目录 {os.path.dirname(dst_path)}")
            print("请使用 sudo 运行程序：sudo python3 main.py")
            print("\n按回车键返回主菜单...")
            input()
            return False
        
        # 覆盖拷贝（使用进度条）
        if os.path.exists(dst_path):
            shutil.rmtree(dst_path)
        copy_with_progress(src_path, dst_path, "拷贝后端文件")
        print("后端文件拷贝完成！")
        return True
    except PermissionError:
        print(f"\n错误: 权限不足，无法拷贝文件")
        print("请使用 sudo 运行程序：sudo python3 main.py")
        print("\n按回车键返回主菜单...")
        input()
        return False
    except Exception as e:
        print(f"拷贝失败: {e}")
        print("\n按回车键返回主菜单...")
        input()
        return False


def auto_detect_backend(model_name: str, config: Dict) -> Optional[str]:
    """根据模型名称自动检测后端类型"""
    # 获取目标CFe-B卡设备
    target_device = get_target_cfeb_device()
    if not target_device:
        print("错误: 未设置目标CFe-B卡，请先进行系统设置")
        print("\n按回车键返回主菜单...")
        input()
        return None
    
    # 获取目标CFe-B卡第二个分区的挂载点（models分区）
    mount_point = get_mount_point(f'{target_device}2')
    if not mount_point:
        print(f"错误: {target_device}2未挂载，请先挂载该分区")
        print("\n按回车键返回主菜单...")
        input()
        return None
    
    yaml_path = os.path.join(mount_point, '98autoshell', 'backend_list.yaml')
    if not os.path.exists(yaml_path):
        print(f"警告: 未找到backend_list.yaml: {yaml_path}")
        return None
    
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            backend_list = yaml.safe_load(f)
        
        if not backend_list:
            return None
        
        # 检查模型在哪个后端列表中
        for backend, models in backend_list.items():
            if isinstance(models, list):
                # 检查完整匹配或部分匹配
                for m in models:
                    if model_name == m or model_name in m or m in model_name:
                        return backend
            elif isinstance(models, str):
                # 如果是字符串，尝试分割（支持逗号、空格等分隔符）
                model_list = re.split(r'[,，\s]+', models.strip())
                model_list = [m.strip() for m in model_list if m.strip()]
                for m in model_list:
                    if model_name == m or model_name in m or m in model_name:
                        return backend
        
        return None
    except Exception as e:
        print(f"读取backend_list.yaml失败: {e}")
        return None


def select_manufacturer() -> str:
    """选择模型厂商"""
    print("\n=== 请选择要写入的模型厂商 ===")
    for key, value in MANUFACTURERS.items():
        print()
        print(f"{key}. {value}")
    
    while True:
        choice = input("\n请输入选项 (1-7): ").strip()
        if choice in MANUFACTURERS:
            return MANUFACTURERS[choice]
        print("无效选择，请输入1-7之间的数字")


def filter_models_by_manufacturer(manufacturer: str, models: List[Dict]) -> List[Dict]:
    """根据厂商过滤模型"""
    filtered = []
    known_manufacturers = ['Qwen', 'GPT', 'Llama', 'DeepSeek', 'Gemma', 'ZhipuAI']
    
    for model in models:
        model_manufacturer = model['manufacturer']
        # 如果厂商匹配，或者用户选择了Others且模型不在已知厂商列表中
        if manufacturer == 'Others':
            if model_manufacturer not in known_manufacturers:
                filtered.append(model)
        else:
            if model_manufacturer == manufacturer:
                filtered.append(model)
    
    return filtered


def select_model(models: List[Dict]) -> Optional[Dict]:
    """选择模型"""
    if not models:
        print("没有可用的模型")
        return None
    
    print("\n=== 请选择模型 ===")
    for i, model in enumerate(models, 1):
        print()
        print(f"{i}. {model['full_name']}")
    
    while True:
        try:
            choice = int(input(f"\n请输入选项编号 (1-{len(models)}): ").strip())
            if 1 <= choice <= len(models):
                return models[choice - 1]
            else:
                print(f"无效的选项，请输入1-{len(models)}之间的数字")
        except ValueError:
            print("请输入有效的数字")


def copy_model(model: Dict):
    """拷贝模型到目标CFe-B卡的models分区/llm"""
    src_path = model['path']
    
    # 获取目标CFe-B卡设备
    target_device = get_target_cfeb_device()
    if not target_device:
        print("错误: 未设置目标CFe-B卡，请先进行系统设置")
        print("\n按回车键返回主菜单...")
        input()
        return False
    
    # 获取目标CFe-B卡第二个分区的挂载点（models分区）
    mount_point = get_mount_point(f'{target_device}2')
    if not mount_point:
        print(f"错误: {target_device}2未挂载，请先挂载该分区")
        print("\n按回车键返回主菜单...")
        input()
        return False
    
    dst_path = os.path.join(mount_point, 'llm')
    
    # 检查挂载点是否可写
    if not os.access(mount_point, os.W_OK):
        print(f"\n错误: 权限不足，无法写入 {mount_point}")
        print("请检查以下事项：")
        print("1. 是否以root权限运行程序（建议使用 sudo）")
        print("2. 挂载点的权限设置")
        print(f"3. 当前用户是否有权限访问 {mount_point}")
        print("\n按回车键返回主菜单...")
        input()
        return False
    
    # 确保目标目录存在
    try:
        os.makedirs(dst_path, exist_ok=True)
    except PermissionError:
        print(f"\n错误: 权限不足，无法创建目录 {dst_path}")
        print("请检查以下事项：")
        print("1. 是否以root权限运行程序（建议使用 sudo python3 main.py）")
        print("2. 挂载点的权限设置")
        print(f"3. 当前用户是否有权限在 {mount_point} 下创建目录")
        print("\n按回车键返回主菜单...")
        input()
        return False
    except Exception as e:
        print(f"\n错误: 创建目录失败: {e}")
        print("\n按回车键返回主菜单...")
        input()
        return False
    
    print(f"\n正在拷贝模型...")
    print(f"源: {src_path}")
    print(f"目标: {dst_path}")
    
    try:
        # 使用进度条拷贝
        copy_with_progress(src_path, os.path.join(dst_path, model['full_name']), 
                          f"拷贝模型 {model['full_name']}")
        print("模型拷贝完成！")
        return True
    except PermissionError:
        print(f"\n错误: 权限不足，无法拷贝文件到 {dst_path}")
        print("请使用 sudo 运行程序：sudo python3 main.py")
        print("\n按回车键返回主菜单...")
        input()
        return False
    except Exception as e:
        print(f"拷贝失败: {e}")
        print("\n按回车键返回主菜单...")
        input()
        return False


def ask_dev_config() -> Tuple[bool, Optional[str]]:
    """询问是否生成dev模式配置文件"""
    print("\n是否自动生成dev模式模型拉起配置文件？")
    while True:
        choice = input("请输入 y/n: ").strip().lower()
        if choice in ['y', 'yes', '是']:
            break
        elif choice in ['n', 'no', '否']:
            return False, None
        print("无效输入，请输入 y 或 n")
    
    print("\n请选择显存大小:")
    print()
    print("1. 32G")
    print()
    print("2. 48G")
    print()
    print("3. 64G")
    print()
    print("4. 128G")
    
    vram_map = {
        '1': '32G',
        '2': '48G',
        '3': '64G',
        '4': '128G'
    }
    
    while True:
        vram_choice = input("\n请输入选项 (1-4): ").strip()
        if vram_choice in vram_map:
            return True, vram_map[vram_choice]
        print("无效选择，请输入1-4之间的数字")


def copy_dev_config_files(disk_path: str, vram: str, model_full_name: str) -> bool:
    """拷贝dev模式配置文件
    
    Args:
        disk_path: 用户选择的磁盘路径
        vram: 显存大小（如 '32G', '48G', '64G', '128G'）
        model_full_name: 模型的完整文件夹名称
    
    Returns:
        bool: 是否成功
    """
    # 构建源路径：磁盘路径/Model_dev_yaml/显存大小/模型名称
    model_dev_yaml_path = os.path.join(disk_path, 'Model_dev_yaml')
    
    if not os.path.exists(model_dev_yaml_path):
        print(f"错误: 未找到Model_dev_yaml文件夹: {model_dev_yaml_path}")
        print("\n按回车键返回主菜单...")
        input()
        return False
    
    # 检查显存大小对应的文件夹
    vram_folder = os.path.join(model_dev_yaml_path, vram)
    if not os.path.exists(vram_folder):
        print(f"错误: 未找到显存文件夹: {vram_folder}")
        print("\n按回车键返回主菜单...")
        input()
        return False
    
    # 检查模型对应的文件夹
    model_config_folder = os.path.join(vram_folder, model_full_name)
    if not os.path.exists(model_config_folder):
        print(f"错误: 未找到模型配置文件夹: {model_config_folder}")
        print("\n按回车键返回主菜单...")
        input()
        return False
    
    # 需要拷贝的三个文件
    config_files = {
        'embedding_run.yaml': 'embedding',
        'llm_run.yaml': 'llm',
        'reranker_run.yaml': 'reranker'
    }
    
    # 获取目标CFe-B卡设备
    target_device = get_target_cfeb_device()
    if not target_device:
        print("错误: 未设置目标CFe-B卡，请先进行系统设置")
        print("\n按回车键返回主菜单...")
        input()
        return False
    
    # 获取目标CFe-B卡第二个分区的挂载点（models分区）
    mount_point = get_mount_point(f'{target_device}2')
    if not mount_point:
        print(f"错误: {target_device}2未挂载，请先挂载该分区")
        print("\n按回车键返回主菜单...")
        input()
        return False
    
    # 检查挂载点是否可写
    if not os.access(mount_point, os.W_OK):
        print(f"\n错误: 权限不足，无法写入 {mount_point}")
        print("请使用 sudo 运行程序：sudo python3 main.py")
        print("\n按回车键返回主菜单...")
        input()
        return False
    
    print(f"\n正在拷贝dev模式配置文件（{vram}显存）...")
    print(f"源目录: {model_config_folder}")
    print(f"目标分区: {target_device}2 (挂载点: {mount_point})")
    print("-" * 50)
    
    success_count = 0
    for filename, target_dir_name in config_files.items():
        src_file = os.path.join(model_config_folder, filename)
        dst_dir = os.path.join(mount_point, 'dev', target_dir_name)
        
        if not os.path.exists(src_file):
            print(f"⚠ 警告: 未找到文件 {filename}，跳过")
            continue
        
        # 确保目标目录存在
        try:
            os.makedirs(dst_dir, exist_ok=True)
        except PermissionError:
            print(f"\n错误: 权限不足，无法创建目录 {dst_dir}")
            print("请使用 sudo 运行程序：sudo python3 main.py")
            print("\n按回车键返回主菜单...")
            input()
            return False
        
        # 目标文件路径
        dst_file = os.path.join(dst_dir, filename)
        
        try:
            # 拷贝文件（使用进度条）
            copy_with_progress(src_file, dst_file, f"拷贝 {filename}")
            target_device = get_target_cfeb_device() or '/dev/sda'
            print(f"✓ {filename} -> {target_device}2/dev/{target_dir_name}/{filename}")
            success_count += 1
        except Exception as e:
            print(f"✗ 拷贝 {filename} 失败: {e}")
            import traceback
            traceback.print_exc()
    
    if success_count == len(config_files):
        print(f"\n所有dev模式配置文件拷贝完成！共 {success_count} 个文件")
        return True
    elif success_count > 0:
        print(f"\n部分dev模式配置文件拷贝完成！成功 {success_count}/{len(config_files)} 个文件")
        return True
    else:
        print("\n错误: 没有成功拷贝任何配置文件")
        print("\n按回车键返回主菜单...")
        input()
        return False


def verify_target_cfeb_card() -> bool:
    """验证并找到目标CFe-B卡
    
    Returns:
        bool: True表示验证通过，False表示验证失败
    """
    print(f"\n正在扫描所有磁盘设备，查找目标CFe-B卡...")
    
    # 使用find_target_cfeb_card函数扫描所有磁盘
    disk_device = find_target_cfeb_card()
    
    if not disk_device:
        print("\n未找到完全对应的目标CFe-B卡")
        print("请检查硬件连接，确保目标CFe-B卡已正确插入（分区标签应为: rootfs, models, app）")
        print("按回车键返回主菜单...")
        input()
        return False
    
    # 获取分区标签信息用于显示
    partitions = {
        'rootfs': f'{disk_device}1',
        'models': f'{disk_device}2',
        'app': f'{disk_device}3'
    }
    
    print("\n正在获取分区详细信息...")
    try:
        result = subprocess.run(['blkid'], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        
        partition_labels = {}
        for line in lines:
            for name, path in partitions.items():
                if path in line:
                    label_match = re.search(r'LABEL="([^"]+)"', line)
                    if label_match:
                        partition_labels[name] = label_match.group(1)
                    else:
                        label_match = re.search(r"LABEL='([^']+)'", line)
                        if label_match:
                            partition_labels[name] = label_match.group(1)
        
        # 验证通过，保存配置并显示信息
        print(f"\n✓ 验证成功！")
        print(f"目标CFe-B卡: {disk_device}")
        print("分区信息:")
        for name, path in partitions.items():
            label = partition_labels.get(name, '未知')
            print(f"  - {name}: {path} (标签: {label})")
        
        # 保存配置
        config = load_config()
        config['target_cfeb_card'] = disk_device
        config['target_partitions'] = partition_labels
        save_config(config)
        
        print(f"\n配置已保存")
        print("按回车键继续，或输入0返回主菜单")
        user_input = input("> ").strip()
        if user_input == '0':
            return False
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"获取分区信息失败: {e}")
        print("\n未找到完全对应的目标CFe-B卡")
        print("请检查硬件连接，确保目标CFe-B卡已正确插入")
        print("按回车键返回主菜单...")
        input()
        return False
    except FileNotFoundError:
        print("错误: 未找到blkid命令，无法验证分区标签")
        print("\n未找到完全对应的目标CFe-B卡")
        print("请检查硬件连接，确保目标CFe-B卡已正确插入")
        print("按回车键返回主菜单...")
        input()
        return False


def run():
    """主运行流程"""
    print("\n" + "="*50)
    print("RM-01 CFe-B存储卡制作工具")
    print("="*50)
    
    # 加载配置
    config = load_config()
    
    # 检查配置
    if not config.get('disk_path') or not config.get('models'):
        print("\n警告: 未进行系统设置，请先进行系统设置")
        print("按回车键返回主菜单...")
        input()
        return
    
    # 验证目标CFe-B卡
    if not verify_target_cfeb_card():
        return
    
    # 选择后端类型（使用循环确保输入有效）
    print("\n=== 请选择后端类型 ===")
    print()
    print("1. FlashAttention")
    print()
    print("2. FlashInfer")
    print()
    print("3. 不清楚，自动适配")
    
    while True:
        backend_choice = input("\n请输入选项 (1-3): ").strip()
        if backend_choice in ['1', '2', '3']:
            break
        print("无效选择，请输入1-3之间的数字")
    
    # 先选择厂商和模型
    # 选择厂商
    manufacturer = select_manufacturer()
    
    # 过滤模型
    filtered_models = filter_models_by_manufacturer(manufacturer, config['models'])
    
    if not filtered_models:
        print(f"未找到 {manufacturer} 厂商的模型")
        print("\n按回车键返回主菜单...")
        input()
        return
    
    # 选择模型
    selected_model = select_model(filtered_models)
    if not selected_model:
        print("\n按回车键返回主菜单...")
        input()
        return
    
    # 根据后端选择拷贝后端文件
    if backend_choice == '3':
        # 自动适配：根据模型确定后端
        backend_type = auto_detect_backend(selected_model['model_name'], config)
        if backend_type:
            print(f"\n自动检测到后端类型: {backend_type}")
            # 根据检测结果拷贝
            if backend_type == 'FlashAttention':
                if not copy_backend('1', config):
                    print("\n按回车键返回主菜单...")
                    input()
                    return
            elif backend_type == 'FlashInfer':
                if not copy_backend('2', config):
                    print("\n按回车键返回主菜单...")
                    input()
                    return
        else:
            print("无法自动检测后端类型，请手动选择")
            print("\n按回车键返回主菜单...")
            input()
            return
    elif backend_choice in ['1', '2']:
        # 用户手动选择的后端：直接拷贝对应的后端
        if not copy_backend(backend_choice, config):
            print("\n按回车键返回主菜单...")
            input()
            return
    
    # 拷贝模型
    if not copy_model(selected_model):
        print("\n按回车键返回主菜单...")
        input()
        return
    
    # 询问是否生成dev配置文件
    need_dev_config, vram = ask_dev_config()
    if not need_dev_config:
        # 用户选择不生成dev配置文件
        print("\n" + "="*50)
        print("存储卡制作完成！")
        print("="*50)
        print("\n请选择操作：")
        print("0. 返回主菜单")
        while True:
            choice = input("> ").strip()
            if choice == '0':
                return
            print("请输入0返回主菜单")
    
    # 拷贝dev模式配置文件
    if not copy_dev_config_files(config['disk_path'], vram, selected_model['full_name']):
        print("\n按回车键返回主菜单...")
        input()
        return
    
    # 存储卡制作完成
    print("\n" + "="*50)
    print("存储卡制作完成！")
    print("="*50)
    print("\n请选择操作：")
    print("0. 返回主菜单")
    while True:
        choice = input("> ").strip()
        if choice == '0':
            return
        print("请输入0返回主菜单")


def ask_optimization_config() -> bool:
    """询问是否添加模型优化与推理加速配置文件"""
    print("\n是否要添加模型优化与推理加速配置文件？")
    print()
    print("1. 是")
    print()
    print("2. 否")
    
    while True:
        choice = input("\n请输入选项 (1-2): ").strip()
        if choice == '1':
            return True
        elif choice == '2':
            return False
        print("无效选择，请输入1或2")


def copy_fused_moe_config(disk_path: str, vram: str, model_full_name: str) -> bool:
    """拷贝fused_moe配置文件
    
    Args:
        disk_path: 用户选择的磁盘路径
        vram: 显存大小（如 '32G', '48G', '64G', '128G'）
        model_full_name: 模型的完整文件夹名称
    
    Returns:
        bool: 是否成功
    """
    # 构建源路径：磁盘路径/fused_moe/平台文件夹/模型名称
    fused_moe_path = os.path.join(disk_path, 'fused_moe')
    
    if not os.path.exists(fused_moe_path):
        print(f"错误: 未找到fused_moe文件夹: {fused_moe_path}")
        print("\n按回车键返回主菜单...")
        input()
        return False
    
    # 根据显存大小选择平台文件夹
    # 32G, 48G, 64G -> Orin
    # 128G -> Thor
    if vram == '128G':
        platform_folder = 'Thor'
    else:
        platform_folder = 'Orin'
    
    platform_path = os.path.join(fused_moe_path, platform_folder)
    if not os.path.exists(platform_path):
        print(f"错误: 未找到平台文件夹: {platform_path}")
        print("\n按回车键返回主菜单...")
        input()
        return False
    
    # 检查模型对应的文件夹
    model_config_folder = os.path.join(platform_path, model_full_name)
    if not os.path.exists(model_config_folder):
        print(f"错误: 未找到模型配置文件夹: {model_config_folder}")
        print("\n按回车键返回主菜单...")
        input()
        return False
    
    # 获取目标CFe-B卡设备
    target_device = get_target_cfeb_device()
    if not target_device:
        print("错误: 未设置目标CFe-B卡，请先进行系统设置")
        print("\n按回车键返回主菜单...")
        input()
        return False
    
    # 获取目标CFe-B卡第一个分区的挂载点（rootfs分区）
    mount_point = get_mount_point(f'{target_device}1')
    if not mount_point:
        print(f"错误: {target_device}1未挂载，请先挂载该分区")
        print("\n按回车键返回主菜单...")
        input()
        return False
    
    # 检查挂载点是否可写
    if not os.access(mount_point, os.W_OK):
        print(f"\n错误: 权限不足，无法写入 {mount_point}")
        print("请使用 sudo 运行程序：sudo python3 main.py")
        print("\n按回车键返回主菜单...")
        input()
        return False
    
    # 目标路径
    target_dir = os.path.join(mount_point, 'home', 'rm01', 'miniconda3', 'envs', 'vllm', 
                              'lib', 'python3.12', 'site-packages', 'vllm', 
                              'model_executor', 'layers', 'fused_moe', 'configs')
    
    print(f"\n正在拷贝fused_moe配置文件（{platform_folder}平台）...")
    print(f"源目录: {model_config_folder}")
    print(f"目标目录: {target_dir}")
    print("-" * 50)
    
    # 确保目标目录存在
    try:
        os.makedirs(target_dir, exist_ok=True)
    except PermissionError:
        print(f"\n错误: 权限不足，无法创建目录 {target_dir}")
        print("请使用 sudo 运行程序：sudo python3 main.py")
        print("\n按回车键返回主菜单...")
        input()
        return False
    except Exception as e:
        print(f"\n错误: 创建目录失败: {e}")
        print("\n按回车键返回主菜单...")
        input()
        return False
    
    # 拷贝文件夹内的所有文件
    copied_files = []
    failed_files = []
    
    try:
        for item in os.listdir(model_config_folder):
            src_item = os.path.join(model_config_folder, item)
            dst_item = os.path.join(target_dir, item)
            
            if os.path.isfile(src_item):
                # 拷贝文件
                try:
                    copy_with_progress(src_item, dst_item, f"拷贝 {item}")
                    copied_files.append(item)
                    print(f"✓ {item}")
                except Exception as e:
                    failed_files.append(item)
                    print(f"✗ {item} 拷贝失败: {e}")
            elif os.path.isdir(src_item):
                # 拷贝目录
                try:
                    copy_with_progress(src_item, dst_item, f"拷贝目录 {item}")
                    copied_files.append(f"{item}/")
                    print(f"✓ {item}/")
                except Exception as e:
                    failed_files.append(f"{item}/")
                    print(f"✗ {item}/ 拷贝失败: {e}")
        
        if copied_files:
            print(f"\n✓ fused_moe配置文件拷贝完成！")
            print(f"成功拷贝 {len(copied_files)} 个项目")
            if failed_files:
                print(f"警告: {len(failed_files)} 个项目拷贝失败")
            return True
        else:
            print("\n错误: 没有成功拷贝任何文件")
            print("\n按回车键返回主菜单...")
            input()
            return False
            
    except Exception as e:
        print(f"\n错误: 拷贝fused_moe配置文件失败: {e}")
        import traceback
        traceback.print_exc()
        print("\n按回车键返回主菜单...")
        input()
        return False


def unmount_sda():
    """卸载目标CFe-B卡磁盘"""
    # 获取目标CFe-B卡设备
    target_device = get_target_cfeb_device()
    if not target_device:
        print("\n未设置目标CFe-B卡，跳过卸载")
        return
    
    print(f"\n正在卸载{target_device}磁盘...")
    
    # 尝试卸载所有目标CFe-B卡的分区
    partitions = [f'{target_device}1', f'{target_device}2', f'{target_device}3']
    unmounted = []
    
    for partition in partitions:
        mount_point = get_mount_point(partition)
        if mount_point:
            try:
                result = subprocess.run(['umount', partition], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    print(f"✓ 已卸载 {partition}")
                    unmounted.append(partition)
                else:
                    print(f"⚠ 卸载 {partition} 失败: {result.stderr.strip()}")
            except subprocess.TimeoutExpired:
                print(f"⚠ 卸载 {partition} 超时")
            except Exception as e:
                print(f"⚠ 卸载 {partition} 时出错: {e}")
    
    if unmounted:
        print(f"\n已成功卸载 {len(unmounted)} 个分区")
    else:
        print("\n没有需要卸载的分区，或卸载失败")
    
    # 尝试使用udisksctl卸载（如果可用）
    try:
        result = subprocess.run(['udisksctl', 'unmount', '-b', target_device], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✓ 使用udisksctl卸载成功")
    except:
        pass


def check_root_permission():
    """检查是否以root权限运行"""
    try:
        if os.geteuid() != 0:
            print("\n" + "="*50)
            print("⚠ 警告: 建议以root权限运行此程序")
            print("="*50)
            print("如果遇到权限问题（如无法创建目录或拷贝文件），")
            print("请使用以下命令运行：")
            print("  sudo python3 main.py")
            print("或")
            print("  sudo ./run.sh")
            print("="*50 + "\n")
            return False
        return True
    except AttributeError:
        # Windows系统没有geteuid
        return True


def scan_existing_models() -> List[str]:
    """扫描目标CFe-B卡的models分区/llm下已存在的模型文件夹"""
    # 获取目标CFe-B卡设备
    target_device = get_target_cfeb_device()
    if not target_device:
        return []
    
    # 获取目标CFe-B卡第二个分区的挂载点（models分区）
    mount_point = get_mount_point(f'{target_device}2')
    if not mount_point:
        return []
    
    llm_path = os.path.join(mount_point, 'llm')
    if not os.path.exists(llm_path):
        return []
    
    models = []
    try:
        for item in os.listdir(llm_path):
            item_path = os.path.join(llm_path, item)
            if os.path.isdir(item_path):
                models.append(item)
    except Exception:
        return []
    
    return models


def add_optimization_config_standalone():
    """独立添加模型优化与推理加速配置文件功能"""
    print("\n" + "="*50)
    print("添加模型优化与推理加速配置文件")
    print("="*50)
    
    # 检查配置，需要disk_path来找到fused_moe文件夹
    config = load_config()
    if not config.get('disk_path'):
        print("\n错误: 未进行系统设置，请先进行系统设置")
        print("需要设置硬盘路径以找到fused_moe配置文件")
        print("\n请先完成系统设置，按回车键返回主菜单...")
        input()
        return
    
    # 扫描已存在的模型
    print("\n正在扫描存储卡中已存在的模型...")
    existing_models = scan_existing_models()
    
    if not existing_models:
        print("未找到任何模型文件夹")
        target_device = get_target_cfeb_device() or '/dev/sda'
        print(f"请确保 {target_device}2/llm/ 目录下已有模型")
        print("\n请检查硬件连接或确保目标CFe-B卡已正确插入，按回车键返回主菜单...")
        input()
        return
    
    print(f"\n找到 {len(existing_models)} 个模型:")
    for i, model in enumerate(existing_models, 1):
        print(f"  {i}. {model}")
    
    # 选择显存大小
    print("\n请选择显存大小:")
    print()
    print("1. 32G")
    print()
    print("2. 48G")
    print()
    print("3. 64G")
    print()
    print("4. 128G")
    
    vram_map = {
        '1': '32G',
        '2': '48G',
        '3': '64G',
        '4': '128G'
    }
    
    while True:
        vram_choice = input("\n请输入选项 (1-4): ").strip()
        if vram_choice in vram_map:
            vram = vram_map[vram_choice]
            break
        print("无效选择，请输入1-4之间的数字")
    
    # 为每个模型添加配置文件
    print(f"\n开始为 {len(existing_models)} 个模型添加优化配置文件（{vram}显存）...")
    print("-" * 50)
    
    success_count = 0
    failed_models = []
    
    for model_name in existing_models:
        print(f"\n处理模型: {model_name}")
        if copy_fused_moe_config(config['disk_path'], vram, model_name):
            success_count += 1
        else:
            failed_models.append(model_name)
    
    # 显示结果
    print("\n" + "="*50)
    print("处理完成！")
    print("="*50)
    print(f"成功: {success_count}/{len(existing_models)} 个模型")
    if failed_models:
        print(f"失败: {len(failed_models)} 个模型")
        print("失败的模型:")
        for model in failed_models:
            print(f"  - {model}")
    
    print("\n请选择操作：")
    print("0. 返回主菜单")
    while True:
        choice = input("> ").strip()
        if choice == '0':
            return
        print("请输入0返回主菜单")


def main():
    """主函数"""
    # 检查root权限
    check_root_permission()
    
    while True:
        # 显示Logo
        print("\n")
        print("    ██████╗ ███╗   ███╗██╗███╗   ██╗████████╗███████╗")
        print("    ██╔══██╗████╗ ████║██║████╗  ██║╚══██╔══╝██╔════╝")
        print("    ██████╔╝██╔████╔██║██║██╔██╗ ██║   ██║   █████╗  ")
        print("    ██╔══██╗██║╚██╔╝██║██║██║╚██╗██║   ██║   ██╔══╝  ")
        print("    ██║  ██║██║ ╚═╝ ██║██║██║ ╚████║   ██║   ███████╗")
        print("    ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝")
        print("")
        print("\n" + "-"*50)
        print("RM-01 CFe-B存储卡制作工具")
        print("RM-01 CFe-B Card Maker Tool")
        print("-"*50)
        
        # 菜单选项（加粗显示）
        print()
        print("\033[1m1. 系统设置 / System Settings\033[0m")
        print()
        print("\033[1m2. 制作模型卡 / Create Model Card\033[0m")
        print()
        print("\033[1m3. 添加模型优化与推理加速配置文件 / Add Model Optimization Config\033[0m")
        print()
        print("\033[1m4. 退出 / Exit\033[0m")
        print()
        print()
        print("-"*50)
        print("Copyright RMinte 泛灵人工智能")
        print("-"*50)
        
        choice = input("\n请选择功能 (1-4): ").strip()
        
        if choice == '1':
            system_settings()
        elif choice == '2':
            run()
        elif choice == '3':
            add_optimization_config_standalone()
        elif choice == '4':
            print("感谢使用！")
            # 卸载磁盘
            unmount_sda()
            break
        else:
            print("无效的选项，请重新选择")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序已中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

