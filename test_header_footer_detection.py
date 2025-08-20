#!/usr/bin/env python3
"""
测试页眉页脚检测算法的修复效果
"""

import os
import sys
import json
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from pdf_analyzer import PdfAnalyzer

def test_detection_algorithms(pdf_path: str):
    """测试各种检测算法"""
    print(f"测试PDF文件: {pdf_path}")
    print("=" * 60)
    
    if not os.path.exists(pdf_path):
        print(f"错误: 文件不存在 {pdf_path}")
        return
    
    try:
        # 测试1: Artifact检测
        print("\n1. Artifact检测结果:")
        print("-" * 30)
        analyzer = PdfAnalyzer()
        artifact_result = analyzer.extract_artifact_headers_footers(pdf_path, max_pages=5)
        print(json.dumps(artifact_result, ensure_ascii=False, indent=2))
        
        # 测试2: 启发式检测
        print("\n2. 启发式检测结果:")
        print("-" * 30)
        heuristic_result = analyzer.detect_headers_footers_heuristic(pdf_path, max_pages=5)
        print(json.dumps(heuristic_result, ensure_ascii=False, indent=2))
        
        # 测试3: 综合检测
        print("\n3. 综合检测结果:")
        print("-" * 30)
        combined_result = analyzer.extract_all_headers_footers(pdf_path, max_pages=5)
        print(json.dumps(combined_result, ensure_ascii=False, indent=2))
        
        # 分析结果
        print("\n4. 检测结果分析:")
        print("-" * 30)
        analyze_results(artifact_result, heuristic_result, combined_result)
        
    except Exception as e:
        print(f"检测过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

def analyze_results(artifact_result, heuristic_result, combined_result):
    """分析检测结果"""
    
    # 统计检测到的页眉页脚数量
    artifact_headers = sum(len(p.get("header", [])) for p in artifact_result.get("pages", []))
    artifact_footers = sum(len(p.get("footer", [])) for p in artifact_result.get("pages", []))
    
    heuristic_headers = sum(len(p.get("headers", [])) for p in heuristic_result.get("pages", []))
    heuristic_footers = sum(len(p.get("footers", [])) for p in heuristic_result.get("pages", []))
    
    combined_headers = sum(len(p.get("header", [])) for p in combined_result.get("pages", []))
    combined_footers = sum(len(p.get("footer", [])) for p in combined_result.get("pages", []))
    
    print(f"Artifact检测: 页眉 {artifact_headers} 个, 页脚 {artifact_footers} 个")
    print(f"启发式检测: 页眉 {heuristic_headers} 个, 页脚 {heuristic_footers} 个")
    print(f"综合检测: 页眉 {combined_headers} 个, 页脚 {combined_footers} 个")
    
    # 检测重复内容
    print(f"\n检测到的候选页眉页脚:")
    if "header_candidates" in heuristic_result:
        print("页眉候选:")
        for candidate in heuristic_result["header_candidates"][:5]:  # 显示前5个
            print(f"  - {candidate['text']} (出现{candidate['count']}次, 标签: {candidate['labels']})")
    
    if "footer_candidates" in heuristic_result:
        print("页脚候选:")
        for candidate in heuristic_result["footer_candidates"][:5]:  # 显示前5个
            print(f"  - {candidate['text']} (出现{candidate['count']}次, 标签: {candidate['labels']})")

def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("用法: python test_header_footer_detection.py <PDF文件路径>")
        print("示例: python test_header_footer_detection.py test.pdf")
        return
    
    pdf_path = sys.argv[1]
    test_detection_algorithms(pdf_path)

if __name__ == "__main__":
    main()
