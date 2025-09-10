import dspy
import os
import json
from typing import Optional
from dspy.adapters import JSONAdapter

class ModelManager:
    _current_model: str = None
    _adapter = JSONAdapter()
    _model_map = {}
    _providers = {}
    _initialized = False

    @classmethod
    def _load_configurations(cls):
        """Load configurations from JSON files"""
        if cls._initialized:
            return
        
        providers_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'providers.json')
        try:
            with open(providers_path, 'r') as f:
                cls._providers = json.load(f)
        except FileNotFoundError:
            cls._providers = {}
        
        models_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models.json')
        try:
            with open(models_path, 'r') as f:
                config = json.load(f)
                
                # Handle both old array format and new object format
                if isinstance(config, list):
                    models_config = config
                    default_model = models_config[0]['label'] if models_config else None
                else:
                    models_config = config.get('models', [])
                    default_model = config.get('default')
                
                cls._model_map = {}
                
                for model in models_config:
                    label = model['label']
                    name = model['name']
                    
                    if 'provider' in model and model['provider'] in cls._providers:
                        provider_config = cls._providers[model['provider']]
                        api_base = provider_config['api_base']
                        api_key = os.getenv(provider_config['api_key_env'], '')
                    else:
                        api_base = model.get('api_base', '')
                        api_key_env = model.get('api_key_env', '')
                        api_key = os.getenv(api_key_env, '') if api_key_env else ''
                    
                    cls._model_map[label] = {
                        'name': name,
                        'api_key': api_key,
                        'api_base': api_base,
                    }
                
                # Set default model if not already set
                if cls._current_model is None and default_model and default_model in cls._model_map:
                    cls._current_model = default_model
                elif cls._current_model is None and cls._model_map:
                    cls._current_model = list(cls._model_map.keys())[0]
                    
        except FileNotFoundError:
            cls._model_map = {}
        
        cls._initialized = True

    @classmethod
    def add_model(cls, model_name: str, name: str, provider: str = None):
        """
        Dynamically add a new model to the model map.
        Only allows known providers. Uses os.getenv to fetch the API key for the provider.
        """
        cls._load_configurations()
        
        if not provider or provider not in cls._providers:
            raise ValueError(f"Unknown or missing provider: {provider}. Allowed: {list(cls._providers.keys())}")
        
        preset = cls._providers[provider]
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
        cls._load_configurations()
        return list(cls._model_map.keys())

    @classmethod
    def get_current_model_name(cls):
        cls._load_configurations()
        return cls._current_model

    @classmethod
    def set_model(cls, model_name: str) -> bool:
        cls._load_configurations()
        if model_name not in cls._model_map:
            return False
        cls._current_model = model_name
        return True

    @classmethod
    def has_model(cls, model_name: str) -> bool:
        cls._load_configurations()
        return model_name in cls._model_map

    @classmethod
    def get_lm(cls, model_name: Optional[str] = None):
        cls._load_configurations()
        cfg = cls._model_map[cls._current_model if model_name is None else model_name]
        return dspy.LM(cfg['name'], api_key=cfg['api_key'], api_base=cfg['api_base'], max_tokens=10_000)

    @classmethod
    def get_adapter(cls):
        return cls._adapter
