# Gepeto Data Collection System

This document describes the data collection system implemented for Gepeto to gather training data and optimize the AI agent's performance.

## Overview

The data collection system captures every interaction with Gepeto, storing both the input context (chat messages, user information) and the model's response (trajectory, reasoning, tool usage). This data is essential for:

1. **Training Data**: Chat contexts serve as training samples for improving the model
2. **Optimization**: Prediction data helps optimize tool usage and reasoning patterns
3. **Performance Analysis**: Metrics for understanding and improving Gepeto's effectiveness

## Architecture

### Data Structure

The system uses a versioned approach with three main data types:

#### 1. Chat Context Data (`ChatContextData`)
- **Purpose**: Training samples representing the input to the model
- **Contains**:
  - Chat events and messages
  - User and channel information
  - Model configuration
  - Metadata (user count, message types, etc.)

#### 2. Prediction Data (`PredictionData`)
- **Purpose**: Model responses and execution details for optimization
- **Contains**:
  - ReAct trajectory steps
  - Internal reasoning processes
  - Tool usage patterns
  - Performance metrics (execution time, success rate)
  - Error information

#### 3. Session Metadata
- **Purpose**: Links context and prediction data for complete interactions
- **Contains**:
  - Session identifiers
  - File paths to related data
  - Timestamps and version information

### Directory Structure

```
data/gepeto_training/
├── chat_contexts/
│   └── 1.0/                    # Version 1.0 data
│       ├── context_<session>_<timestamp>.json
│       └── ...
├── predictions/
│   └── 1.0/
│       ├── prediction_<session>_<timestamp>.json
│       └── ...
└── metadata/
    ├── session_<session_id>.json
    └── ...
```

## Data Collection Process

### Automatic Collection

The data collection is integrated into the main `act()` function and runs automatically:

1. **Start Timer**: Records execution start time
2. **Execute Model**: Runs the DSPy ReAct agent
3. **Capture Results**: Extracts trajectory, reasoning, and tool usage
4. **Calculate Metrics**: Measures execution time and success rate
5. **Save Data**: Stores both context and prediction data with unique session ID

### Data Versioning

The system supports versioning to handle changes in data format:

- **Current Version**: 1.0
- **Version Enum**: `DataVersion` enum manages version constants
- **Backward Compatibility**: Different versions can coexist in separate directories

## Usage

### Basic Data Collection

Data collection happens automatically when Gepeto processes messages. No manual intervention is required.

### Accessing Collected Data

```python
from src.data_collector import get_data_collector

# Get the data collector instance
collector = get_data_collector()

# Retrieve training data
training_data = collector.get_training_data()

# Get statistics
stats = collector.get_statistics()
```

### Manual Data Collection

For custom scenarios, you can manually collect data:

```python
from src.data_collector import collect_interaction_data

# Collect data for a specific interaction
result = collect_interaction_data(
    chat_context_data={
        'events': messages,
        'chat_id': chat_id,
        'chat_name': chat_name,
        'chat_type': chat_type,
        # ... other context data
    },
    prediction_result=model_result,
    execution_time_ms=execution_time,
    success=True,
    model_name='gpt-4',
    model_config={'temperature': 0.7}
)
```

## Data Analysis

### Analysis Script

Use the provided analysis script to examine collected data:

```bash
python scripts/analyze_data.py
```

This generates:
- Comprehensive analysis report
- Tool usage statistics
- Success/failure patterns
- Chat interaction patterns
- ReAct trajectory analysis

### Key Metrics

The analysis provides insights into:

1. **Tool Usage Patterns**
   - Most frequently used tools
   - Tool success rates
   - Average execution times per tool

2. **Chat Interaction Patterns**
   - Message length statistics
   - Response time analysis
   - Chat type distribution

3. **Success/Failure Analysis**
   - Overall success rates
   - Failure reason categorization
   - Success rates by context type

4. **ReAct Trajectory Analysis**
   - Average trajectory length
   - Reasoning vs. action step ratios
   - Pattern identification

## Data Privacy and Security

### Privacy Considerations

- **User Data**: Chat messages and user information are stored locally
- **Anonymization**: Consider implementing user ID hashing for production
- **Retention**: Implement data retention policies as needed

### Security Measures

- **Local Storage**: All data is stored locally in the `data/` directory
- **Access Control**: Ensure proper file permissions on data directories
- **Encryption**: Consider encrypting sensitive data files

## Optimization Use Cases

### Training Data Preparation

The collected chat contexts can be used to:
- Fine-tune language models on domain-specific conversations
- Create training datasets for response generation
- Develop conversation pattern recognition

### Model Optimization

Prediction data enables:
- Tool usage optimization
- Reasoning pattern improvement
- Performance bottleneck identification
- Error pattern analysis

### A/B Testing

The versioned data structure supports:
- Comparing different model configurations
- Evaluating prompt engineering changes
- Testing new tool implementations

## Configuration

### Environment Variables

```bash
# Optional: Custom data directory
GEPETO_DATA_PATH=/path/to/custom/data/directory
```

### Data Collector Settings

```python
# Custom data collector initialization
from src.data_collector import DataCollector

collector = DataCollector(base_path="/custom/path")
```

## Maintenance

### Data Cleanup

Implement periodic cleanup to manage disk space:

```python
# Example cleanup script
import os
from datetime import datetime, timedelta
from pathlib import Path

def cleanup_old_data(days_to_keep=30):
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    # Implement cleanup logic based on file timestamps
```

### Monitoring

Monitor data collection health:
- Check for write permissions
- Monitor disk space usage
- Verify data integrity
- Track collection success rates

## Troubleshooting

### Common Issues

1. **Permission Errors**
   - Ensure write permissions on data directory
   - Check disk space availability

2. **Import Errors**
   - Verify `data_collector.py` is in the correct path
   - Check Python path configuration

3. **Data Format Issues**
   - Check for version compatibility
   - Validate JSON file structure

### Debug Mode

Enable debug logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

### Planned Features

1. **Real-time Analytics Dashboard**
2. **Automated Model Retraining Pipeline**
3. **Advanced Privacy Controls**
4. **Cloud Storage Integration**
5. **Performance Optimization Suggestions**

### Contributing

When adding new data collection features:
1. Update the version number if changing data structure
2. Maintain backward compatibility
3. Add appropriate tests
4. Update this documentation

## Examples

### Example Session Data

**Chat Context Example:**
```json
{
  "version": "1.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "events": [...],
  "chat_id": 123456789,
  "chat_name": "general",
  "chat_type": "text",
  "model_name": "gpt-4",
  "user_count": 3,
  "message_count": 15,
  "contains_images": false
}
```

**Prediction Example:**
```json
{
  "version": "1.0",
  "timestamp": "2024-01-15T10:30:05Z",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "trajectory": [...],
  "reasoning": {...},
  "execution_time_ms": 1250.5,
  "success": true,
  "tools_used": ["send_message", "search"],
  "tool_call_count": 2
}
```

This data collection system provides a robust foundation for improving Gepeto through data-driven optimization and training.