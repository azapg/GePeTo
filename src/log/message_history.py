import json
import os

from .log_util import load_json, save_json

short_message_history = {
    'messages': []
}

MESSAGE_HISTORY_FILE = './data/message_history.json'

def log_message(message):
    """
    Saves the message to the message history json file.
    """
    if os.path.exists(MESSAGE_HISTORY_FILE):
        all_message_history = load_json(MESSAGE_HISTORY_FILE)
    else:
        all_message_history = {'messages': []}
        
    all_message_history['messages'].append(message)
        
    save_json(MESSAGE_HISTORY_FILE, all_message_history)    
    
def add_to_message_history(message):
    """
    Add a message to the message history.

    Args:
        message (dict): The message to add, should contain 'id', 'content', 'author_id', 'author_name',
                        'author_display_name', 'channel_id', and 'timestamp'.
    """
    short_message_history['messages'].append(message)
    if len(short_message_history['messages']) > 100:
        short_message_history['messages'].pop(0)

    log_message(message)
    
    
def get_message_history():
    """
    Get the message history.

    Returns:
        list: A list of messages in the message history.
    """
    return short_message_history['messages']