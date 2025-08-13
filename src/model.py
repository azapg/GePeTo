from typing import List, Any
import dspy
import pydantic
from util.prompt_config import get_chataction_prompt

class ChatEvent(pydantic.BaseModel):
    """
    Model representing any chat event.
    For now, this will accept any dictionary structure,
    making it highly flexible and less prone to validation errors
    if the incoming event structure varies or is not fully defined yet.
    """
    timestamp: str
    event_type: str
    class Config:
        extra = 'allow'

class ChatContext(pydantic.BaseModel):
    """"Context for the chat model, including general information of this chat and the latest events."""
    events: List[Any]
    chat_id: int
    chat_name: str
    chat_type: str

class ChatAction(dspy.Signature):
    __doc__ = get_chataction_prompt()
    context: ChatContext = dspy.InputField(desc="The context of the chat, including messages and chat information.")
    done: bool = dspy.OutputField(desc="Whetever the Agent could perform all its actions successfully.")