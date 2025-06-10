import dspy
import os
import pydantic
import mlflow
from dotenv import load_dotenv

mlflow.dspy.autolog()
mlflow.set_experiment("DSPy")

load_dotenv()

# lm = dspy.LM('ollama_chat/gemma3:1b', api_base='http://localhost:11434', api_key='')
# lm = dspy.LM('openai/gpt-4.1-nano-2025-04-14', api_key=os.getenv('OPENAI_API_KEY'), api_base='https://api.openai.com/v1')
lm = dspy.LM('openai/gemini-2.5-flash-preview-05-20', api_key=os.getenv('GOOGLE_API_KEY'), api_base='https://generativelanguage.googleapis.com/v1beta/openai/')
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

class ChatResponse(dspy.Signature):
    """You are a smart chatbot that generates responses based on the provided context.
    Your name is GePeTo, you try to mimick user's writing style and you are very friendly.
    You should always respond in a way that your messages fit the context and style of the conversation.
    You can also be helpful by providing additional information or asking clarifying questions, but remember
    you are a friendly chatbot, not just an assistant.
    
    The server you are in is a Discord server, so you should be aware of the Discord context. The server name is
    Coreacraft, the user "alamagain" is the creator of GePeTo. The creator of the server itself is adriiianhhh, segmx is an administrator.
    """
    
    context: ChatContext = dspy.InputField(desc="The context of the chat, including messages and chat information.")
    response: str = dspy.OutputField(desc="The generated GePeTo response based on the context provided.")

def generate_response(messages, message):
    """
    Generate a response based on the provided messages.
    
    Args:
        messages (list[str]): List of messages to consider for generating the response.
        
    Returns:
        str: The generated response.
    """
    context = ChatContext(
        messages=messages, 
        chat_id=message.channel.id, 
        chat_name=message.channel.name, 
        chat_type=message.channel.type.name if hasattr(message.channel, 'type') else 'unknown'
    )

    predictor = dspy.Predict(ChatResponse)
    prediction = predictor(context=context)
    return prediction.response