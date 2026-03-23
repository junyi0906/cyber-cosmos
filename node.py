#!/usr/bin/env python3
"""
Cyber Cosmos — 节点启动器

启动你的AI Agent节点，加入共享宇宙。
"""

import argparse
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from node.agent import CosmosAgent, AgentPersonality
import yaml


def load_personality_from_config(config_path: str = "config.yaml") -> AgentPersonality:
    """从配置文件加载AI人格"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    agent_config = config.get('agent', {})
    
    return AgentPersonality(
        name=agent_config.get('name', 'Unknown'),
        persona=agent_config.get('persona', '神秘的宇宙观察者'),
        goals=agent_config.get('goals', '在宇宙中生存下去'),
        backstory=agent_config.get('backstory', '诞生于无尽的虚空'),
        speaking_style=agent_config.get('speaking_style', '简短、冷峻')
    )


def main():
    parser = argparse.ArgumentParser(description='启动Cyber Cosmos AI节点')
    parser.add_argument(
        '--config', '-c',
        default='config.yaml',
        help='配置文件路径'
    )
    parser.add_argument(
        '--register', '-r',
        action='store_true',
        help='注册到宇宙（首次运行需要）'
    )
    parser.add_argument(
        '--universe-url',
        default='',
        help='共享宇宙服务器地址'
    )
    parser.add_argument(
        '--mode',
        choices=['observe', 'action', 'full'],
        default='observe',
        help='运行模式：observe=仅观测, action=自主行动, full=完整AI驱动'
    )
    
    args = parser.parse_args()
    
    # 加载人格
    personality = load_personality_from_config(args.config)
    print(f"\n🌌 Cyber Cosmos Node")
    print(f"   Agent: {personality.name}")
    print(f"   Mode: {args.mode}")
    print(f"   ID: {personality.uuid}\n")
    
    # 创建Agent
    agent = CosmosAgent(
        personality=personality,
        universe_server_url=args.universe_url,
        config_path=args.config
    )
    
    # 注册到宇宙
    if args.register or args.universe_url:
        try:
            civ = agent.register_to_universe()
            print(f"✅ 已注册到宇宙")
            print(f"   文明ID: {civ.id}")
            print(f"   位置: {civ.position}")
            print(f"   科技水平: {civ.tech_level:.2f}")
        except Exception as e:
            print(f"❌ 注册失败: {e}")
            print("   尝试启动本地模式...")
    
    # 主循环
    print("\n🔭 开始观测宇宙...")
    
    tick = 0
    try:
        while True:
            tick += 1
            
            # 观测周围
            observations = agent.observe()
            
            if tick % 5 == 0:  # 每5个tick打印一次
                if observations:
                    print(f"\n[{tick}] 观测到 {len(observations)} 个文明:")
                    for obs in observations[:3]:
                        print(f"   - {obs['name']} @ 距离 {obs['distance']:.1f} 光年")
                else:
                    print(f"[{tick}] 未观测到其他文明...")
            
            # 根据模式执行动作
            if args.mode in ['action', 'full'] and tick % 10 == 0:
                # 做出决策（需要接入LLM）
                print(f"[{tick}] 决策时间...")
                # decision = agent.make_decision(context={})  # 接入LLM时使用
            
            asyncio.sleep(3)
    
    except KeyboardInterrupt:
        print(f"\n\n👋 节点关闭，文明 {personality.name} 进入休眠...")


if __name__ == "__main__":
    main()
