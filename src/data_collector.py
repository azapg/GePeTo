import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import asyncio
from dataclasses import dataclass, asdict
from enum import Enum

class DataVersion(Enum):
    """Versioning for data format changes"""
    V1_0 = "1.0"
    CURRENT = V1_0

@dataclass
class ChatContextData:
    """Structured representation of chat context for training"""
    version: str
    timestamp: str
    session_id: str
    
    # Chat context information
    events: List[Dict[str, Any]]
    chat_id: int
    chat_name: str
    chat_type: str
    
    # Model and system information
    model_name: str
    model_config: Dict[str, Any]
    
    # Additional metadata
    user_count: int
    message_count: int
    contains_images: bool
    contains_attachments: bool

@dataclass
class PredictionData:
    """Structured representation of model prediction/response"""
    version: str
    timestamp: str
    session_id: str
    
    # Core prediction data
    trajectory: Optional[List[Dict[str, Any]]]  # ReAct trajectory steps
    reasoning: Optional[Dict[str, Any]]  # Internal reasoning steps
    final_output: Optional[Dict[str, Any]]  # Final response/actions
    
    # Execution metadata
    execution_time_ms: float
    success: bool
    error_message: Optional[str]
    
    # Tool usage tracking
    tools_used: List[str]
    tool_call_count: int
    
    # Performance metrics for optimization
    tokens_used: Optional[int]
    cost_estimate: Optional[float]

class DataCollector:
    """Main data collection system for Gepeto"""
    
    def __init__(self, base_path: str = "data/gepeto_training"):
        self.base_path = Path(base_path)
        self.chat_context_path = self.base_path / "chat_contexts"
        self.predictions_path = self.base_path / "predictions"
        self.metadata_path = self.base_path / "metadata"
        
        # Create directory structure
        self._setup_directories()
        
        # Session tracking
        self.current_session_id = None
        
    def _setup_directories(self):
        """Create the directory structure for data storage"""
        directories = [
            self.chat_context_path,
            self.predictions_path,
            self.metadata_path,
            self.chat_context_path / DataVersion.CURRENT.value,
            self.predictions_path / DataVersion.CURRENT.value,
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            
    def start_session(self) -> str:
        """Start a new data collection session"""
        self.current_session_id = str(uuid.uuid4())
        return self.current_session_id
        
    def get_current_session_id(self) -> str:
        """Get current session ID, create one if none exists"""
        if not self.current_session_id:
            self.start_session()
        return self.current_session_id
        
    def save_chat_context(
        self,
        events: List[Any],
        chat_id: int,
        chat_name: str,
        chat_type: str,
        model_name: str,
        model_config: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> str:
        """Save chat context data for training"""
        
        if session_id is None:
            session_id = self.get_current_session_id()
            
        # Analyze events for metadata
        user_count = len(set(event.get('author', {}).get('id') for event in events if event.get('author')))
        message_count = len(events)
        contains_images = any(event.get('attachments') or event.get('embeds') for event in events)
        contains_attachments = any(event.get('attachments') for event in events)
        
        # Create structured data
        context_data = ChatContextData(
            version=DataVersion.CURRENT.value,
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            events=events,
            chat_id=chat_id,
            chat_name=chat_name,
            chat_type=chat_type,
            model_name=model_name,
            model_config=model_config,
            user_count=user_count,
            message_count=message_count,
            contains_images=contains_images,
            contains_attachments=contains_attachments
        )
        
        # Save to file
        filename = f"context_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_path = self.chat_context_path / DataVersion.CURRENT.value / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(context_data), f, indent=2, ensure_ascii=False, default=str)
            
        return str(file_path)
        
    def save_prediction(
        self,
        result: Any,  # DSPy ReAct result object
        execution_time_ms: float,
        success: bool = True,
        error_message: Optional[str] = None,
        session_id: Optional[str] = None,
        model_name: Optional[str] = None,
        tokens_used: Optional[int] = None,
        cost_estimate: Optional[float] = None
    ) -> str:
        """Save prediction/response data for optimization"""
        
        if session_id is None:
            session_id = self.get_current_session_id()
            
        # Extract data from DSPy result object
        trajectory = None
        reasoning = None
        final_output = None
        tools_used = []
        tool_call_count = 0
        
        try:
            # Try to extract trajectory (ReAct agent specific)
            if hasattr(result, 'trajectory'):
                trajectory = result.trajectory
                
            # Try to extract reasoning
            if hasattr(result, 'reasoning'):
                reasoning = result.reasoning
                
            # Try to extract the final output/done status
            if hasattr(result, 'done'):
                final_output = {'done': result.done}
                
            # Analyze trajectory for tool usage
            if trajectory:
                for step in trajectory:
                    if isinstance(step, dict):
                        if 'tool_name' in step:
                            tools_used.append(step['tool_name'])
                            tool_call_count += 1
                        elif 'action' in step:
                            # Alternative format
                            action = step.get('action', '')
                            if action and action != 'finish':
                                tools_used.append(action)
                                tool_call_count += 1
                                
            # Remove duplicates while preserving order
            tools_used = list(dict.fromkeys(tools_used))
            
        except Exception as e:
            print(f"Warning: Could not fully extract prediction data: {e}")
            # Store raw result as fallback
            final_output = {'raw_result': str(result)}
            
        # Create structured data
        prediction_data = PredictionData(
            version=DataVersion.CURRENT.value,
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            trajectory=trajectory,
            reasoning=reasoning,
            final_output=final_output,
            execution_time_ms=execution_time_ms,
            success=success,
            error_message=error_message,
            tools_used=tools_used,
            tool_call_count=tool_call_count,
            tokens_used=tokens_used,
            cost_estimate=cost_estimate
        )
        
        # Save to file
        filename = f"prediction_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_path = self.predictions_path / DataVersion.CURRENT.value / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(prediction_data), f, indent=2, ensure_ascii=False, default=str)
            
        return str(file_path)
        
    def save_interaction(
        self,
        chat_context_data: Dict[str, Any],
        prediction_result: Any,
        execution_time_ms: float,
        success: bool = True,
        error_message: Optional[str] = None,
        model_name: Optional[str] = None,
        model_config: Optional[Dict[str, Any]] = None,
        tokens_used: Optional[int] = None,
        cost_estimate: Optional[float] = None
    ) -> Dict[str, str]:
        """Save both chat context and prediction data for a complete interaction"""
        
        session_id = self.start_session()  # New session for each interaction
        
        # Save chat context
        context_file = self.save_chat_context(
            events=chat_context_data.get('events', []),
            chat_id=chat_context_data.get('chat_id', 0),
            chat_name=chat_context_data.get('chat_name', 'unknown'),
            chat_type=chat_context_data.get('chat_type', 'unknown'),
            model_name=model_name or 'unknown',
            model_config=model_config or {},
            session_id=session_id
        )
        
        # Save prediction
        prediction_file = self.save_prediction(
            result=prediction_result,
            execution_time_ms=execution_time_ms,
            success=success,
            error_message=error_message,
            session_id=session_id,
            model_name=model_name,
            tokens_used=tokens_used,
            cost_estimate=cost_estimate
        )
        
        # Save session metadata
        self._save_session_metadata(session_id, context_file, prediction_file)
        
        return {
            'session_id': session_id,
            'context_file': context_file,
            'prediction_file': prediction_file
        }
        
    def _save_session_metadata(self, session_id: str, context_file: str, prediction_file: str):
        """Save metadata linking context and prediction files"""
        metadata = {
            'session_id': session_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'context_file': context_file,
            'prediction_file': prediction_file,
            'version': DataVersion.CURRENT.value
        }
        
        metadata_file = self.metadata_path / f"session_{session_id}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
            
    def get_training_data(
        self,
        version: Optional[str] = None,
        limit: Optional[int] = None,
        filter_successful: bool = True
    ) -> List[Dict[str, Any]]:
        """Retrieve training data with optional filtering"""
        
        if version is None:
            version = DataVersion.CURRENT.value
            
        training_data = []
        metadata_files = list(self.metadata_path.glob("session_*.json"))
        
        if limit:
            metadata_files = metadata_files[:limit]
            
        for metadata_file in metadata_files:
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    
                # Load context data
                with open(metadata['context_file'], 'r', encoding='utf-8') as f:
                    context_data = json.load(f)
                    
                # Load prediction data
                with open(metadata['prediction_file'], 'r', encoding='utf-8') as f:
                    prediction_data = json.load(f)
                    
                # Filter if requested
                if filter_successful and not prediction_data.get('success', True):
                    continue
                    
                training_data.append({
                    'session_id': metadata['session_id'],
                    'context': context_data,
                    'prediction': prediction_data
                })
                
            except Exception as e:
                print(f"Warning: Could not load training data from {metadata_file}: {e}")
                continue
                
        return training_data
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about collected data"""
        
        stats = {
            'total_sessions': 0,
            'successful_interactions': 0,
            'failed_interactions': 0,
            'total_tools_used': set(),
            'average_execution_time': 0,
            'data_versions': set(),
            'date_range': {'earliest': None, 'latest': None}
        }
        
        metadata_files = list(self.metadata_path.glob("session_*.json"))
        stats['total_sessions'] = len(metadata_files)
        
        execution_times = []
        timestamps = []
        
        for metadata_file in metadata_files:
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    
                with open(metadata['prediction_file'], 'r', encoding='utf-8') as f:
                    prediction_data = json.load(f)
                    
                if prediction_data.get('success', True):
                    stats['successful_interactions'] += 1
                else:
                    stats['failed_interactions'] += 1
                    
                execution_times.append(prediction_data.get('execution_time_ms', 0))
                stats['total_tools_used'].update(prediction_data.get('tools_used', []))
                stats['data_versions'].add(prediction_data.get('version', 'unknown'))
                timestamps.append(prediction_data.get('timestamp'))
                
            except Exception as e:
                print(f"Warning: Could not process {metadata_file} for statistics: {e}")
                continue
                
        if execution_times:
            stats['average_execution_time'] = sum(execution_times) / len(execution_times)
            
        if timestamps:
            timestamps = [t for t in timestamps if t]  # Remove None values
            if timestamps:
                stats['date_range']['earliest'] = min(timestamps)
                stats['date_range']['latest'] = max(timestamps)
                
        # Convert sets to lists for JSON serialization
        stats['total_tools_used'] = list(stats['total_tools_used'])
        stats['data_versions'] = list(stats['data_versions'])
        
        return stats

# Global instance for easy access
_data_collector = None

def get_data_collector() -> DataCollector:
    """Get the global data collector instance"""
    global _data_collector
    if _data_collector is None:
        _data_collector = DataCollector()
    return _data_collector

def collect_interaction_data(
    chat_context_data: Dict[str, Any],
    prediction_result: Any,
    execution_time_ms: float,
    success: bool = True,
    error_message: Optional[str] = None,
    model_name: Optional[str] = None,
    model_config: Optional[Dict[str, Any]] = None,
    tokens_used: Optional[int] = None,
    cost_estimate: Optional[float] = None
) -> Dict[str, str]:
    """Convenience function to collect interaction data"""
    collector = get_data_collector()
    return collector.save_interaction(
        chat_context_data=chat_context_data,
        prediction_result=prediction_result,
        execution_time_ms=execution_time_ms,
        success=success,
        error_message=error_message,
        model_name=model_name,
        model_config=model_config,
        tokens_used=tokens_used,
        cost_estimate=cost_estimate
    )