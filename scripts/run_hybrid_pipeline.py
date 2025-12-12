#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混合推荐系统全流程编排
执行顺序：cleanup → data_processor → vectorizer → train_cf
"""

import logging
import sys
import time
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def print_separator(title: str = "", char: str = "=", width: int = 80):
    """打印分隔线"""
    if title:
        side_len = (width - len(title) - 2) // 2
        print(f"\n{char * side_len} {title} {char * side_len}")
    else:
        print(f"\n{char * width}")


def print_step_header(step_num: int, step_name: str, script_name: str):
    """打印步骤头部"""
    print_separator()
    print(f"🚀 步骤 {step_num}: {step_name}")
    print(f"   脚本: {script_name}")
    print_separator("", char="-")


def run_step(step_num: int, step_name: str, script_name: str, module_path: str):
    """运行单个步骤"""
    print_step_header(step_num, step_name, script_name)
    
    start_time = time.time()
    
    try:
        # 动态导入并执行
        sys.path.insert(0, str(SCRIPTS_DIR))
        
        module_name = script_name.replace('.py', '')
        module = __import__(module_name)
        
        if hasattr(module, 'main'):
            result = module.main()
            elapsed = time.time() - start_time
            
            print_separator("", char="-")
            print(f"✅ 步骤 {step_num} 完成！耗时: {elapsed:.2f} 秒")
            print_separator()
            
            return True, result
        else:
            logger.error(f"❌ 模块 {module_name} 没有 main() 函数")
            return False, None
            
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ 步骤 {step_num} 失败: {e}")
        logger.error(f"   耗时: {elapsed:.2f} 秒")
        print_separator()
        return False, None


def main():
    """主流程"""
    print_separator(" 混合推荐系统 - 全流程执行 ", char="=")
    print(f"\n项目根目录: {PROJECT_ROOT}")
    print(f"脚本目录: {SCRIPTS_DIR}")
    print(f"\n执行计划:")
    print("  步骤 1: 环境清理 (cleanup.py)")
    print("  步骤 2: 数据处理 (data_processor_bge.py)")
    print("  步骤 3: 向量化 (vectorizer_bge.py)")
    print("  步骤 4: 模型训练 (train_cf.py)")
    print_separator()
    
    input("\n按 Enter 开始执行...")
    
    total_start = time.time()
    
    # 步骤 1: 环境清理
    success, _ = run_step(
        1,
        "环境清理",
        "cleanup.py",
        "cleanup"
    )
    
    if not success:
        logger.warning("⚠️  环境清理失败，但继续执行...")
    
    # 步骤 2: 数据处理
    success, result = run_step(
        2,
        "数据处理 (FMA + Last.fm)",
        "data_processor_bge.py",
        "data_processor_bge"
    )
    
    if not success:
        logger.error("❌ 数据处理失败，流程终止")
        return
    
    # 步骤 3: 向量化
    success, result = run_step(
        3,
        "BGE-M3 向量化 + ChromaDB",
        "vectorizer_bge.py",
        "vectorizer_bge"
    )
    
    if not success:
        logger.error("❌ 向量化失败，流程终止")
        return
    
    # 步骤 4: 模型训练
    success, result = run_step(
        4,
        "LightFM 协同过滤训练",
        "train_cf.py",
        "train_cf"
    )
    
    if not success:
        logger.warning("⚠️  LightFM 训练失败（可能数据格式问题）")
    
    # 总结
    total_elapsed = time.time() - total_start
    
    print_separator(" 全流程执行完成 ", char="=")
    print(f"\n总耗时: {total_elapsed:.2f} 秒 ({total_elapsed/60:.1f} 分钟)")
    print("\n输出位置:")
    print(f"  清洗数据: {PROJECT_ROOT}/data/processed/unified_songs_bge.parquet")
    print(f"  向量库: {PROJECT_ROOT}/index/chroma_bge_m3/")
    print(f"  LightFM 模型: {PROJECT_ROOT}/data/models/lightfm_model.pkl")
    print(f"  ID 映射: {PROJECT_ROOT}/data/models/cf_mappings.pkl")
    print_separator("", char="=")
    
    print("\n🎉 混合推荐系统构建完成！")
    print("   现在可以使用该系统进行音乐推荐了。")
    print_separator("", char="=")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断执行")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 流程执行失败: {e}")
        sys.exit(1)
