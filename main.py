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
    '6': 'Others'
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
    
    # 遍历Models_download下的所有文件夹
    for item in os.listdir(models_path):
        item_path = os.path.join(models_path, item)
        if os.path.isdir(item_path):
            # 解析文件夹名：第一个单词是厂商，后面是模型名
            # 优先使用下划线，如果没有则使用连字符
            if '_' in item:
                parts = item.split('_', 1)  # 使用下划线分割，最多分割一次
            elif '-' in item:
                parts = item.split('-', 1)  # 使用连字符分割，最多分割一次
            else:
                # 如果都没有，整个作为模型名，厂商为Others
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
            print(f"  发现模型: {manufacturer} - {model_name}")
    
    return models


def system_settings():
    """系统设置功能"""
    print("\n=== 系统设置 ===")
    
    # 显示lsblk
    show_lsblk()
    
    # 获取用户输入的硬盘地址（使用循环确保输入有效）
    while True:
        print("\n请输入硬盘地址（例如: /dev/sdb 或 /mnt/usb）:")
        disk_path = input("> ").strip()
        
        if not disk_path:
            print("错误: 硬盘地址不能为空，请重新输入")
            continue
        
        if not os.path.exists(disk_path):
            print(f"错误: 路径不存在: {disk_path}")
            retry = input("是否重新输入？(y/n): ").strip().lower()
            if retry != 'y':
                return
            continue
        
        # 扫描模型
        models = scan_models(disk_path)
        
        if not models:
            print("警告: 未找到任何模型")
            retry = input("是否重新输入路径？(y/n): ").strip().lower()
            if retry != 'y':
                return
            continue
        
        # 保存配置
        config = {
            'disk_path': disk_path,
            'models': models
        }
        save_config(config)
        
        print(f"\n设置已保存！共找到 {len(models)} 个模型")
        break


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


def copy_backend(backend_type: str, config: Dict):
    """拷贝后端文件"""
    disk_path = config.get('disk_path', '')
    if not disk_path:
        print("错误: 未设置硬盘路径，请先进行系统设置")
        return False
    
    # 确定源路径
    if backend_type == '1':  # FlashAttention
        src_path = os.path.join(disk_path, '98autoshell', 'Attention')
    elif backend_type == '2':  # FlashInfer
        src_path = os.path.join(disk_path, '98autoshell', 'Infer')
    else:
        print("错误: 无效的后端类型")
        return False
    
    if not os.path.exists(src_path):
        print(f"错误: 源路径不存在: {src_path}")
        return False
    
    # 获取/dev/sda1的挂载点（第一个分区rm01rootfs）
    mount_point = get_mount_point('/dev/sda1')
    if not mount_point:
        print("错误: /dev/sda1未挂载，请先挂载该分区")
        return False
    
    # 目标路径：挂载点下的/home/rm01/autoShell
    dst_path = os.path.join(mount_point, 'home', 'rm01', 'autoShell')
    
    print(f"\n正在拷贝后端文件...")
    print(f"源: {src_path}")
    print(f"目标: {dst_path}")
    
    try:
        # 确保目标目录的父目录存在
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        
        # 覆盖拷贝（使用进度条）
        if os.path.exists(dst_path):
            shutil.rmtree(dst_path)
        copy_with_progress(src_path, dst_path, "拷贝后端文件")
        print("后端文件拷贝完成！")
        return True
    except Exception as e:
        print(f"拷贝失败: {e}")
        return False


def auto_detect_backend(model_name: str, config: Dict) -> Optional[str]:
    """根据模型名称自动检测后端类型"""
    # 获取/dev/sda2的挂载点（第二个分区rm01models）
    mount_point = get_mount_point('/dev/sda2')
    if not mount_point:
        print("错误: /dev/sda2未挂载，请先挂载该分区")
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
        print(f"{key}. {value}")
    
    while True:
        choice = input("\n请输入选项 (1-6): ").strip()
        if choice in MANUFACTURERS:
            return MANUFACTURERS[choice]
        print("无效选择，请输入1-6之间的数字")


def filter_models_by_manufacturer(manufacturer: str, models: List[Dict]) -> List[Dict]:
    """根据厂商过滤模型"""
    filtered = []
    for model in models:
        model_manufacturer = model['manufacturer']
        # 如果厂商匹配，或者用户选择了Others且模型不在已知厂商列表中
        if manufacturer == 'Others':
            if model_manufacturer not in ['Qwen', 'GPT', 'Llama', 'DeepSeek', 'Gemma']:
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
        print(f"{i}. {model['manufacturer']} - {model['model_name']}")
    
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
    """拷贝模型到/dev/sda2/llm"""
    src_path = model['path']
    
    # 获取/dev/sda2的挂载点（第二个分区rm01models）
    mount_point = get_mount_point('/dev/sda2')
    if not mount_point:
        print("错误: /dev/sda2未挂载，请先挂载该分区")
        return False
    
    dst_path = os.path.join(mount_point, 'llm')
    
    # 确保目标目录存在
    os.makedirs(dst_path, exist_ok=True)
    
    print(f"\n正在拷贝模型...")
    print(f"源: {src_path}")
    print(f"目标: {dst_path}")
    
    try:
        # 使用进度条拷贝
        copy_with_progress(src_path, os.path.join(dst_path, model['full_name']), 
                          f"拷贝模型 {model['full_name']}")
        print("模型拷贝完成！")
        return True
    except Exception as e:
        print(f"拷贝失败: {e}")
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
    print("1. 32G")
    print("2. 48G")
    print("3. 64G")
    print("4. 128G")
    
    vram_map = {
        '1': '32G',
        '2': '48G',
        '3': '64G',
        '4': '128G'
    }
    
    while True:
        vram_choice = input("请输入选项 (1-4): ").strip()
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
        return False
    
    # 检查显存大小对应的文件夹
    vram_folder = os.path.join(model_dev_yaml_path, vram)
    if not os.path.exists(vram_folder):
        print(f"错误: 未找到显存文件夹: {vram_folder}")
        return False
    
    # 检查模型对应的文件夹
    model_config_folder = os.path.join(vram_folder, model_full_name)
    if not os.path.exists(model_config_folder):
        print(f"错误: 未找到模型配置文件夹: {model_config_folder}")
        return False
    
    # 需要拷贝的三个文件
    config_files = {
        'embedding_run.yaml': 'embedding',
        'llm_run.yaml': 'llm',
        'reranker_run.yaml': 'reranker'
    }
    
    # 获取/dev/sda2的挂载点（第二个分区rm01models）
    mount_point = get_mount_point('/dev/sda2')
    if not mount_point:
        print("错误: /dev/sda2未挂载，请先挂载该分区")
        return False
    
    print(f"\n正在拷贝dev模式配置文件（{vram}显存）...")
    print(f"源目录: {model_config_folder}")
    print(f"目标分区: /dev/sda2 (挂载点: {mount_point})")
    print("-" * 50)
    
    success_count = 0
    for filename, target_dir_name in config_files.items():
        src_file = os.path.join(model_config_folder, filename)
        dst_dir = os.path.join(mount_point, 'dev', target_dir_name)
        
        if not os.path.exists(src_file):
            print(f"⚠ 警告: 未找到文件 {filename}，跳过")
            continue
        
        # 确保目标目录存在
        os.makedirs(dst_dir, exist_ok=True)
        
        # 目标文件路径
        dst_file = os.path.join(dst_dir, filename)
        
        try:
            # 拷贝文件（使用进度条）
            copy_with_progress(src_file, dst_file, f"拷贝 {filename}")
            print(f"✓ {filename} -> /dev/sda2/dev/{target_dir_name}/{filename}")
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
        return False


def run():
    """主运行流程"""
    print("\n" + "="*50)
    print("RM-01 CFe-B存储卡制作工具")
    print("="*50)
    
    # 加载配置
    config = load_config()
    
    # 检查分区
    check_partitions()
    
    # 检查配置
    if not config.get('disk_path') or not config.get('models'):
        print("\n警告: 未进行系统设置，请先进行系统设置")
        return
    
    # 选择后端类型（使用循环确保输入有效）
    print("\n=== 请选择后端类型 ===")
    print("1. FlashAttention")
    print("2. FlashInfer")
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
        return
    
    # 选择模型
    selected_model = select_model(filtered_models)
    if not selected_model:
        return
    
    # 根据后端选择拷贝后端文件
    if backend_choice == '3':
        # 自动适配：根据模型确定后端
        backend_type = auto_detect_backend(selected_model['model_name'], config)
        if backend_type:
            print(f"\n自动检测到后端类型: {backend_type}")
            # 根据检测结果拷贝
            if backend_type == 'FlashAttention':
                copy_backend('1', config)
            elif backend_type == 'FlashInfer':
                copy_backend('2', config)
        else:
            print("无法自动检测后端类型，请手动选择")
            return
    elif backend_choice in ['1', '2']:
        # 用户手动选择的后端：直接拷贝对应的后端
        if not copy_backend(backend_choice, config):
            return
    
    # 拷贝模型
    if not copy_model(selected_model):
        return
    
    # 询问是否生成dev配置文件
    need_dev_config, vram = ask_dev_config()
    if not need_dev_config:
        # 用户选择不生成dev配置文件，直接退出程序
        print("\n" + "="*50)
        print("存储卡制作完成！")
        print("="*50)
        print("\n请按0退出程序")
        while True:
            choice = input("> ").strip()
            if choice == '0':
                break
            print("请输入0退出程序")
        # 卸载磁盘并退出程序
        unmount_sda()
        print("\n感谢使用！")
        sys.exit(0)
    
    # 拷贝dev模式配置文件
    copy_dev_config_files(config['disk_path'], vram, selected_model['full_name'])
    
    # 询问是否添加模型优化与推理加速配置文件
    need_optimization_config = ask_optimization_config()
    if need_optimization_config:
        # 拷贝fused_moe配置文件
        copy_fused_moe_config(config['disk_path'], vram, selected_model['full_name'])
    
    # 存储卡制作完成
    print("\n" + "="*50)
    print("存储卡制作完成！")
    print("="*50)
    print("\n请按0退出程序")
    while True:
        choice = input("> ").strip()
        if choice == '0':
            break
        print("请输入0退出程序")
    
    # 卸载磁盘并退出程序
    unmount_sda()
    print("\n感谢使用！")
    sys.exit(0)


def ask_optimization_config() -> bool:
    """询问是否添加模型优化与推理加速配置文件"""
    print("\n是否要添加模型优化与推理加速配置文件？")
    print("1. 是")
    print("2. 否")
    
    while True:
        choice = input("请输入选项 (1-2): ").strip()
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
        return False
    
    # 检查模型对应的文件夹
    model_config_folder = os.path.join(platform_path, model_full_name)
    if not os.path.exists(model_config_folder):
        print(f"错误: 未找到模型配置文件夹: {model_config_folder}")
        return False
    
    # 获取/dev/sda1的挂载点（第一个分区rm01rootfs）
    mount_point = get_mount_point('/dev/sda1')
    if not mount_point:
        print("错误: /dev/sda1未挂载，请先挂载该分区")
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
    os.makedirs(target_dir, exist_ok=True)
    
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
            return False
            
    except Exception as e:
        print(f"\n错误: 拷贝fused_moe配置文件失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def unmount_sda():
    """卸载/dev/sda磁盘"""
    print("\n正在卸载/dev/sda磁盘...")
    
    # 尝试卸载所有/dev/sda的分区
    partitions = ['/dev/sda1', '/dev/sda2', '/dev/sda3']
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
        result = subprocess.run(['udisksctl', 'unmount', '-b', '/dev/sda'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✓ 使用udisksctl卸载成功")
    except:
        pass


def check_root_permission():
    """检查是否以root权限运行"""
    try:
        if os.geteuid() != 0:
            print("警告: 建议以root权限运行此程序以访问设备文件")
            print("如果遇到权限问题，请使用 sudo 运行")
            return False
        return True
    except AttributeError:
        # Windows系统没有geteuid
        return True


def main():
    """主函数"""
    # 检查root权限
    check_root_permission()
    
    while True:
        print("\n" + "="*50)
        print("RM-01 CFe-B存储卡制作工具")
        print("="*50)
        print("1. 系统设置")
        print("2. 运行")
        print("3. 退出")
        
        choice = input("\n请选择功能 (1-3): ").strip()
        
        if choice == '1':
            system_settings()
        elif choice == '2':
            run()
        elif choice == '3':
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

