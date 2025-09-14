from typing import List
from discord import app_commands

from model_manager import ModelManager


async def model_autocomplete(current: str) -> List[app_commands.Choice[str]]:
    models = ModelManager.get_model_names()
    filtered_models = [model for model in models if current.lower() in model.lower()]
    return [
        app_commands.Choice(name=model, value=model)
        for model in filtered_models[:25]
    ]


async def provider_autocomplete(current: str) -> List[app_commands.Choice[str]]:
    try:
        providers_data = ModelManager.get_providers()
        providers = list(providers_data.keys())
        filtered_providers = [provider for provider in providers if current.lower() in provider.lower()]
        return [
            app_commands.Choice(name=provider, value=provider)
            for provider in filtered_providers[:25]
        ]
    except FileNotFoundError:
        return []
