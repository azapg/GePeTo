import dspy
import os
import pydantic
from dotenv import load_dotenv

load_dotenv()

# lm = dspy.LM('ollama_chat/gemma3:1b', api_base='http://localhost:11434', api_key='')
lm = dspy.LM('openai/gpt-4.1-nano-2025-04-14', api_key=os.getenv('OPENAI_API_KEY'), api_base='https://api.openai.com/v1')
dspy.configure(lm=lm)

class Message(pydantic.BaseModel):
    """Model representing a message in the chat."""
    id: int
    content: str
    author_id: int
    author_name: str
    author_display_name: str
    channel_id: int
    timestamp: str

class ChatContext(pydantic.BaseModel):
    """"Context for the chat model, including general information of this chat and the latest exchanged messages."""
    messages: list[Message]
    chat_id: int
    chat_name: str
    chat_type: str

program = dspy.Predict("context: ChatContext -> response")

def generate_response(messages, message):
    """
    Generate a response based on the provided messages.
    
    Args:
        messages (list[str]): List of messages to consider for generating the response.
        
    Returns:
        str: The generated response.
    """
    prediction = program(
        context = ChatContext(
            messages=messages, 
            chat_id=message.channel.id, 
            chat_name=message.channel.name, 
            chat_type=message.channel.type.name if hasattr(message.channel, 'type') else 'unknown'
        )
    )
    return prediction.response