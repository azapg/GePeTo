import json
import os

def load_json(file_path):
    """
    Load a JSON file and return its content.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        dict: The content of the JSON file.
    """
    if not os.path.exists(file_path):
        return {}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)
    
def save_json(file_path, data):
    """
    Save data to a JSON file.

    Args:
        file_path (str): The path to the JSON file.
        data (dict): The data to save.
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
