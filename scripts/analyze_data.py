#!/usr/bin/env python3
"""
Data Analysis Script for Gepeto Training Data

This script analyzes the collected interaction data to provide insights
for training and optimization.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_collector import get_data_collector
import json
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Any

def analyze_tool_usage(training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze tool usage patterns"""
    tool_counts = Counter()
    tool_success_rates = defaultdict(list)
    tool_execution_times = defaultdict(list)
    
    for interaction in training_data:
        prediction = interaction['prediction']
        tools_used = prediction.get('tools_used', [])
        success = prediction.get('success', True)
        execution_time = prediction.get('execution_time_ms', 0)
        
        for tool in tools_used:
            tool_counts[tool] += 1
            tool_success_rates[tool].append(success)
            tool_execution_times[tool].append(execution_time)
    
    # Calculate success rates
    tool_success_stats = {}
    for tool, successes in tool_success_rates.items():
        tool_success_stats[tool] = {
            'success_rate': sum(successes) / len(successes) if successes else 0,
            'total_uses': len(successes),
            'avg_execution_time': sum(tool_execution_times[tool]) / len(tool_execution_times[tool]) if tool_execution_times[tool] else 0
        }
    
    return {
        'tool_counts': dict(tool_counts),
        'tool_success_stats': tool_success_stats,
        'most_used_tools': tool_counts.most_common(10),
        'total_unique_tools': len(tool_counts)
    }

def analyze_chat_patterns(training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze chat interaction patterns"""
    chat_types = Counter()
    message_lengths = []
    response_times = []
    
    for interaction in training_data:
        context = interaction['context']
        prediction = interaction['prediction']
        
        chat_types[context.get('chat_type', 'unknown')] += 1
        
        events = context.get('events', [])
        if events:
            # Analyze message patterns
            for event in events:
                if isinstance(event, dict) and 'content' in event:
                    message_lengths.append(len(event['content']))
        
        response_times.append(prediction.get('execution_time_ms', 0))
    
    return {
        'chat_type_distribution': dict(chat_types),
        'avg_message_length': sum(message_lengths) / len(message_lengths) if message_lengths else 0,
        'avg_response_time_ms': sum(response_times) / len(response_times) if response_times else 0,
        'total_interactions': len(training_data),
        'message_length_stats': {
            'min': min(message_lengths) if message_lengths else 0,
            'max': max(message_lengths) if message_lengths else 0,
            'median': sorted(message_lengths)[len(message_lengths)//2] if message_lengths else 0
        }
    }

def analyze_success_patterns(training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze success/failure patterns"""
    total_interactions = len(training_data)
    successful_interactions = sum(1 for interaction in training_data if interaction['prediction'].get('success', True))
    
    failure_reasons = Counter()
    success_by_chat_type = defaultdict(list)
    success_by_tool_count = defaultdict(list)
    
    for interaction in training_data:
        context = interaction['context']
        prediction = interaction['prediction']
        
        success = prediction.get('success', True)
        chat_type = context.get('chat_type', 'unknown')
        tool_count = prediction.get('tool_call_count', 0)
        
        success_by_chat_type[chat_type].append(success)
        success_by_tool_count[tool_count].append(success)
        
        if not success:
            error_msg = prediction.get('error_message', 'Unknown error')
            failure_reasons[error_msg] += 1
    
    # Calculate success rates by category
    success_rate_by_chat_type = {}
    for chat_type, successes in success_by_chat_type.items():
        success_rate_by_chat_type[chat_type] = sum(successes) / len(successes)
    
    success_rate_by_tool_count = {}
    for tool_count, successes in success_by_tool_count.items():
        success_rate_by_tool_count[tool_count] = sum(successes) / len(successes)
    
    return {
        'overall_success_rate': successful_interactions / total_interactions if total_interactions > 0 else 0,
        'total_successful': successful_interactions,
        'total_failed': total_interactions - successful_interactions,
        'failure_reasons': dict(failure_reasons),
        'success_rate_by_chat_type': success_rate_by_chat_type,
        'success_rate_by_tool_count': success_rate_by_tool_count
    }

def analyze_trajectory_patterns(training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze ReAct trajectory patterns"""
    trajectory_lengths = []
    reasoning_steps = []
    
    for interaction in training_data:
        prediction = interaction['prediction']
        trajectory = prediction.get('trajectory', [])
        
        if trajectory:
            trajectory_lengths.append(len(trajectory))
            
            # Count reasoning steps vs action steps
            reasoning_count = 0
            action_count = 0
            
            for step in trajectory:
                if isinstance(step, dict):
                    if 'thought' in str(step).lower() or 'reasoning' in str(step).lower():
                        reasoning_count += 1
                    elif 'action' in str(step).lower() or 'tool' in str(step).lower():
                        action_count += 1
            
            reasoning_steps.append({
                'reasoning_steps': reasoning_count,
                'action_steps': action_count,
                'total_steps': len(trajectory)
            })
    
    avg_reasoning_ratio = 0
    if reasoning_steps:
        total_reasoning = sum(step['reasoning_steps'] for step in reasoning_steps)
        total_actions = sum(step['action_steps'] for step in reasoning_steps)
        avg_reasoning_ratio = total_reasoning / (total_reasoning + total_actions) if (total_reasoning + total_actions) > 0 else 0
    
    return {
        'avg_trajectory_length': sum(trajectory_lengths) / len(trajectory_lengths) if trajectory_lengths else 0,
        'trajectory_length_stats': {
            'min': min(trajectory_lengths) if trajectory_lengths else 0,
            'max': max(trajectory_lengths) if trajectory_lengths else 0,
            'median': sorted(trajectory_lengths)[len(trajectory_lengths)//2] if trajectory_lengths else 0
        },
        'avg_reasoning_to_action_ratio': avg_reasoning_ratio,
        'total_trajectories_analyzed': len(trajectory_lengths)
    }

def generate_report(analysis_results: Dict[str, Any]) -> str:
    """Generate a comprehensive analysis report"""
    report = []
    report.append("=" * 60)
    report.append("GEPETO TRAINING DATA ANALYSIS REPORT")
    report.append("=" * 60)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # Overall Statistics
    if 'collector_stats' in analysis_results:
        stats = analysis_results['collector_stats']
        report.append("OVERALL STATISTICS")
        report.append("-" * 30)
        report.append(f"Total Sessions: {stats['total_sessions']}")
        report.append(f"Successful Interactions: {stats['successful_interactions']}")
        report.append(f"Failed Interactions: {stats['failed_interactions']}")
        report.append(f"Average Execution Time: {stats['average_execution_time']:.2f}ms")
        report.append(f"Data Versions: {', '.join(stats['data_versions'])}")
        report.append("")
    
    # Tool Usage Analysis
    if 'tool_analysis' in analysis_results:
        tool_analysis = analysis_results['tool_analysis']
        report.append("TOOL USAGE ANALYSIS")
        report.append("-" * 30)
        report.append(f"Total Unique Tools Used: {tool_analysis['total_unique_tools']}")
        report.append("Most Used Tools:")
        for tool, count in tool_analysis['most_used_tools'][:5]:
            success_rate = tool_analysis['tool_success_stats'].get(tool, {}).get('success_rate', 0)
            report.append(f"  {tool}: {count} uses (Success Rate: {success_rate:.2%})")
        report.append("")
    
    # Chat Patterns Analysis
    if 'chat_analysis' in analysis_results:
        chat_analysis = analysis_results['chat_analysis']
        report.append("CHAT INTERACTION PATTERNS")
        report.append("-" * 30)
        report.append(f"Total Interactions: {chat_analysis['total_interactions']}")
        report.append(f"Average Message Length: {chat_analysis['avg_message_length']:.1f} characters")
        report.append(f"Average Response Time: {chat_analysis['avg_response_time_ms']:.2f}ms")
        report.append("Chat Type Distribution:")
        for chat_type, count in chat_analysis['chat_type_distribution'].items():
            report.append(f"  {chat_type}: {count}")
        report.append("")
    
    # Success Patterns Analysis
    if 'success_analysis' in analysis_results:
        success_analysis = analysis_results['success_analysis']
        report.append("SUCCESS/FAILURE ANALYSIS")
        report.append("-" * 30)
        report.append(f"Overall Success Rate: {success_analysis['overall_success_rate']:.2%}")
        report.append(f"Successful Interactions: {success_analysis['total_successful']}")
        report.append(f"Failed Interactions: {success_analysis['total_failed']}")
        
        if success_analysis['failure_reasons']:
            report.append("Top Failure Reasons:")
            for reason, count in list(success_analysis['failure_reasons'].items())[:3]:
                report.append(f"  {reason}: {count}")
        report.append("")
    
    # Trajectory Analysis
    if 'trajectory_analysis' in analysis_results:
        trajectory_analysis = analysis_results['trajectory_analysis']
        report.append("REACT TRAJECTORY ANALYSIS")
        report.append("-" * 30)
        report.append(f"Average Trajectory Length: {trajectory_analysis['avg_trajectory_length']:.1f} steps")
        report.append(f"Reasoning to Action Ratio: {trajectory_analysis['avg_reasoning_to_action_ratio']:.2%}")
        report.append(f"Total Trajectories Analyzed: {trajectory_analysis['total_trajectories_analyzed']}")
        report.append("")
    
    report.append("=" * 60)
    report.append("END OF REPORT")
    report.append("=" * 60)
    
    return "\n".join(report)

def save_analysis_results(analysis_results: Dict[str, Any], output_dir: str = "analysis_output"):
    """Save analysis results to files"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Save raw analysis data
    with open(f"{output_dir}/analysis_results.json", 'w') as f:
        json.dump(analysis_results, f, indent=2, default=str)
    
    # Save report
    report = generate_report(analysis_results)
    with open(f"{output_dir}/analysis_report.txt", 'w') as f:
        f.write(report)
    
    print(f"Analysis results saved to {output_dir}/")

def main():
    """Main analysis function"""
    print("Starting Gepeto training data analysis...")
    
    # Get data collector and load training data
    collector = get_data_collector()
    training_data = collector.get_training_data()
    
    if not training_data:
        print("No training data found. Make sure Gepeto has been running and collecting data.")
        return
    
    print(f"Loaded {len(training_data)} training interactions")
    
    # Perform various analyses
    analysis_results = {}
    
    print("Analyzing tool usage patterns...")
    analysis_results['tool_analysis'] = analyze_tool_usage(training_data)
    
    print("Analyzing chat interaction patterns...")
    analysis_results['chat_analysis'] = analyze_chat_patterns(training_data)
    
    print("Analyzing success/failure patterns...")
    analysis_results['success_analysis'] = analyze_success_patterns(training_data)
    
    print("Analyzing trajectory patterns...")
    analysis_results['trajectory_analysis'] = analyze_trajectory_patterns(training_data)
    
    print("Getting collector statistics...")
    analysis_results['collector_stats'] = collector.get_statistics()
    
    # Generate and display report
    report = generate_report(analysis_results)
    print("\n" + report)
    
    # Save results
    save_analysis_results(analysis_results)
    
    print("\nAnalysis complete! Check the 'analysis_output' directory for detailed results.")

if __name__ == "__main__":
    main()