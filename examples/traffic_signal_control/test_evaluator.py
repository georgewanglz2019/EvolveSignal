#!/usr/bin/env python3
"""
测试修改后的评估器功能
"""

import json
from evaluator import evaluate

def test_evaluator():
    """测试评估器的新功能"""
    
    # 测试程序路径
    test_program_path = "initial_program.py"
    
    print("开始测试修改后的评估器...")
    print("=" * 50)
    
    try:
        # 运行评估
        results = evaluate(test_program_path)
        
        print("\n评估结果:")
        print("-" * 30)
        
        # 打印评分结果（4位小数）
        print(f"综合评分: {results['combined_score']:.4f}")
        print(f"延误评分: {results['delay_score']:.4f}")
        print(f"停车次数评分: {results['stops_score']:.4f}")
        
        # 打印intersection级别指标（2位小数）
        print(f"\n交叉口级别指标:")
        print("-" * 30)
        intersection_metrics = results.get('intersection_metrics', {})
        print(f"平均延误: {intersection_metrics.get('avg_delay', 0):.2f}")
        print(f"平均停车次数: {intersection_metrics.get('avg_stops', 0):.2f}")
        
        # 打印route级别指标（2位小数）
        print(f"\n路线级别指标:")
        print("-" * 30)
        route_metrics = results.get('route_metrics', {})
        
        for scenario_name, routes in route_metrics.items():
            print(f"\n{scenario_name}:")
            for route_name, metrics in routes.items():
                print(f"  {route_name}:")
                print(f"    平均延误: {metrics['avg_delay']:.2f}")
                print(f"    平均停车次数: {metrics['avg_stops']:.2f}")
        
        # 保存详细结果到JSON文件
        with open('evaluation_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n详细结果已保存到 evaluation_results.json")
        
    except Exception as e:
        print(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_evaluator() 