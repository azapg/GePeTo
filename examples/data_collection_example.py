#!/usr/bin/env python3
"""
Example script demonstrating Gepeto's data collection system

This script shows how to:
1. Access collected training data
2. Analyze the data
3. Extract insights for optimization
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_collector import get_data_collector, collect_interaction_data
import json
from datetime import datetime

def demonstrate_data_access():
    """Demonstrate how to access collected data"""
    print("=== Accessing Collected Data ===")
    
    # Get the data collector instance
    collector = get_data_collector()
    
    # Get basic statistics
    stats = collector.get_statistics()
    print(f"Total sessions collected: {stats['total_sessions']}")
    print(f"Successful interactions: {stats['successful_interactions']}")
    print(f"Failed interactions: {stats['failed_interactions']}")
    print(f"Average execution time: {stats['average_execution_time']:.2f}ms")
    print(f"Tools used: {', '.join(stats['total_tools_used'])}")
    print()

def demonstrate_training_data_retrieval():
    """Demonstrate how to retrieve training data"""
    print("=== Retrieving Training Data ===")
    
    collector = get_data_collector()
    
    # Get all training data
    all_data = collector.get_training_data()
    print(f"Total training samples: {len(all_data)}")
    
    # Get only successful interactions
    successful_data = collector.get_training_data(filter_successful=True)
    print(f"Successful training samples: {len(successful_data)}")
    
    # Get limited data for testing
    limited_data = collector.get_training_data(limit=5)
    print(f"Limited training samples: {len(limited_data)}")
    
    # Show example data structure if available
    if all_data:
        example = all_data[0]
        print("\nExample training sample structure:")
        print(f"  Session ID: {example['session_id']}")
        print(f"  Context keys: {list(example['context'].keys())}")
        print(f"  Prediction keys: {list(example['prediction'].keys())}")
        
        # Show context details
        context = example['context']
        print(f"  Chat ID: {context.get('chat_id')}")
        print(f"  Chat type: {context.get('chat_type')}")
        print(f"  Message count: {context.get('message_count', 0)}")
        print(f"  User count: {context.get('user_count', 0)}")
        
        # Show prediction details
        prediction = example['prediction']
        print(f"  Execution time: {prediction.get('execution_time_ms', 0):.2f}ms")
        print(f"  Success: {prediction.get('success', False)}")
        print(f"  Tools used: {prediction.get('tools_used', [])}")
        print(f"  Tool calls: {prediction.get('tool_call_count', 0)}")
    print()

def demonstrate_manual_data_collection():
    """Demonstrate manual data collection"""
    print("=== Manual Data Collection Example ===")
    
    # Example chat context data
    example_context = {
        'events': [
            {
                'id': '12345',
                'content': 'Hello Gepeto, how are you?',
                'author': {'id': '67890', 'name': 'TestUser'},
                'timestamp': datetime.now().isoformat()
            }
        ],
        'chat_id': 123456789,
        'chat_name': 'test-channel',
        'chat_type': 'text',
        'user_id': 67890,
        'user_name': 'TestUser',
        'message_id': 12345,
        'message_content': 'Hello Gepeto, how are you?'
    }
    
    # Example prediction result (simulated)
    class MockPredictionResult:
        def __init__(self):
            self.trajectory = [
                {'thought': 'User is greeting me, I should respond politely'},
                {'action': 'send_message', 'args': {'content': 'Hello! I am doing well, thank you for asking!'}}
            ]
            self.reasoning = {'final_decision': 'respond_with_greeting'}
            self.done = True
    
    mock_result = MockPredictionResult()
    
    # Collect the data
    try:
        result = collect_interaction_data(
            chat_context_data=example_context,
            prediction_result=mock_result,
            execution_time_ms=150.5,
            success=True,
            model_name='gpt-4',
            model_config={'temperature': 0.7, 'max_tokens': 150}
        )
        
        print("Manual data collection successful!")
        print(f"Session ID: {result['session_id']}")
        print(f"Context file: {result['context_file']}")
        print(f"Prediction file: {result['prediction_file']}")
        
    except Exception as e:
        print(f"Manual data collection failed: {e}")
    print()

def demonstrate_data_analysis():
    """Demonstrate basic data analysis"""
    print("=== Basic Data Analysis ===")
    
    collector = get_data_collector()
    training_data = collector.get_training_data()
    
    if not training_data:
        print("No training data available for analysis")
        return
    
    # Analyze tool usage
    tool_usage = {}
    execution_times = []
    success_count = 0
    
    for interaction in training_data:
        prediction = interaction['prediction']
        
        # Count tool usage
        tools_used = prediction.get('tools_used', [])
        for tool in tools_used:
            tool_usage[tool] = tool_usage.get(tool, 0) + 1
        
        # Collect execution times
        exec_time = prediction.get('execution_time_ms', 0)
        execution_times.append(exec_time)
        
        # Count successes
        if prediction.get('success', False):
            success_count += 1
    
    # Display analysis results
    print(f"Total interactions analyzed: {len(training_data)}")
    print(f"Success rate: {success_count / len(training_data) * 100:.1f}%")
    
    if execution_times:
        avg_time = sum(execution_times) / len(execution_times)
        print(f"Average execution time: {avg_time:.2f}ms")
        print(f"Min execution time: {min(execution_times):.2f}ms")
        print(f"Max execution time: {max(execution_times):.2f}ms")
    
    if tool_usage:
        print("Tool usage frequency:")
        sorted_tools = sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)
        for tool, count in sorted_tools[:5]:  # Top 5 tools
            print(f"  {tool}: {count} times")
    print()

def demonstrate_data_export():
    """Demonstrate how to export data for external analysis"""
    print("=== Data Export Example ===")
    
    collector = get_data_collector()
    training_data = collector.get_training_data()
    
    if not training_data:
        print("No data to export")
        return
    
    # Export to JSON for external tools
    export_data = {
        'metadata': {
            'export_timestamp': datetime.now().isoformat(),
            'total_samples': len(training_data),
            'data_version': '1.0'
        },
        'samples': training_data
    }
    
    # Save to file
    output_file = 'exported_training_data.json'
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"Data exported to {output_file}")
        print(f"File size: {os.path.getsize(output_file)} bytes")
        
    except Exception as e:
        print(f"Export failed: {e}")
    print()

def main():
    """Main demonstration function"""
    print("Gepeto Data Collection System - Examples")
    print("=" * 50)
    print()
    
    try:
        # Demonstrate various features
        demonstrate_data_access()
        demonstrate_training_data_retrieval()
        demonstrate_manual_data_collection()
        demonstrate_data_analysis()
        demonstrate_data_export()
        
        print("All demonstrations completed successfully!")
        
    except Exception as e:
        print(f"Demonstration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()