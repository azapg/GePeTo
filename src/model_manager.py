import dspy
import os
from typing import Optional
from dspy.adapters import JSONAdapter

# ModelManager for dynamic model switching
class ModelManager:
    _current_model: str = 'kimi-k2-paid'
    _adapter = JSONAdapter()
    _model_map = {
        'kimi-k2-free': {
            'name': 'openai/moonshotai/kimi-k2-instruct',
            'api_key': os.getenv('GROQ_API_KEY_FREE'),
            'api_base': 'https://api.groq.com/openai/v1',
        },
        'kimi-k2-paid': {
            'name': 'openai/moonshotai/kimi-k2-instruct',
            'api_key': os.getenv('GROQ_API_KEY_PAID'),
            'api_base': 'https://api.groq.com/openai/v1',
        },
        'gpt-4o': {
            'name': 'openai/gpt-4o',
            'api_key': os.getenv('OPENAI_API_KEY'),
            'api_base': 'https://api.openai.com/v1',
        },
        'gpt-4-mini': {
            'name': 'openai/gpt-4.1-mini-2025-04-14',
            'api_key': os.getenv('OPENAI_API_KEY'),
            'api_base': 'https://api.openai.com/v1',
        },
        'gemini': {
            'name': 'openai/gemini-2.0-flash-lite',
            'api_key': os.getenv('GOOGLE_API_KEY'),
            'api_base': 'https://generativelanguage.googleapis.com/v1beta/openai/',
        },
        'llama3': {
            'name': 'openai/llama3.3-70b',
            'api_key': os.getenv('CEREBRAS_API_KEY'),
            'api_base': 'https://api.cerebras.ai/v1',
        },
        'meta-llama': {
            'name': 'openai/meta-llama/Llama-3.3-70B-Instruct',
            'api_key': os.getenv('NEBIUS_API_KEY'),
            'api_base': 'https://api.studio.nebius.com/v1/',
        },
        'gemma': {
            'name': 'ollama_chat/gemma3:1b',
            'api_key': '',
            'api_base': 'http://localhost:11434',
        },
    }

    @classmethod
    def add_model(cls, model_name: str, name: str, provider: str = None):
        """
        Dynamically add a new model to the model map.
        Only allows known providers. Uses os.getenv to fetch the API key for the provider.
        """
        provider_presets = {
            'openai': {
                'api_base': 'https://api.openai.com/v1',
                'api_key_env': 'OPENAI_API_KEY',
            },
            'groq': {
                'api_base': 'https://api.groq.com/openai/v1',
                'api_key_env': 'GROQ_API_KEY_PAID',
            },
            'cerebras': {
                'api_base': 'https://api.cerebras.ai/v1',
                'api_key_env': 'CEREBRAS_API_KEY',
            },
            'nebius': {
                'api_base': 'https://api.studio.nebius.com/v1/',
                'api_key_env': 'NEBIUS_API_KEY',
            },
            'gemini': {
                'api_base': 'https://generativelanguage.googleapis.com/v1beta/openai/',
                'api_key_env': 'GOOGLE_API_KEY',
            },
            'ollama': {
                'api_base': 'http://localhost:11434',
                'api_key_env': '', 
            },
        }
        if not provider or provider not in provider_presets:
            raise ValueError(f"Unknown or missing provider: {provider}. Allowed: {list(provider_presets.keys())}")
        preset = provider_presets[provider]
        api_key = os.getenv(preset['api_key_env'], '')
        api_base = preset['api_base']
        if not api_key and provider != 'ollama':
            raise ValueError(f"API key for provider '{provider}' not found in environment variable '{preset['api_key_env']}'")
        cls._model_map[model_name] = {
            'name': name,
            'api_key': api_key,
            'api_base': api_base,
        }
        return True

    @classmethod
    def get_model_names(cls):
        return list(cls._model_map.keys())

    @classmethod
    def get_current_model_name(cls):
        return cls._current_model

    @classmethod
    def set_model(cls, model_name: str) -> bool:
        if model_name not in cls._model_map:
            return False
        cls._current_model = model_name
        return True

    @classmethod
    def has_model(cls, model_name: str) -> bool:
        return model_name in cls._model_map

    @classmethod
    def get_lm(cls, model_name: Optional[str] = None):
        cfg = cls._model_map[cls._current_model if model_name is None else model_name]
        return dspy.LM(cfg['name'], api_key=cfg['api_key'], api_base=cfg['api_base'], max_tokens=10_000)

    @classmethod
    def get_adapter(cls):
        return cls._adapter
