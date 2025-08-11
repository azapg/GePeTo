import dspy
from typing import Optional
from tools.tools_manager import tool
from model_manager import ModelManager

class ImageContextExtractorSignature(dspy.Signature):
    """Get information about an image"""
    image: dspy.Image = dspy.InputField()
    question: Optional[str] = dspy.InputField(desc="Optional question to extract specific information about an image.")
    context: str = dspy.OutputField()

@tool
async def get_image_context(url, question: Optional[str] = None):
    """
    Get the context of an image from a URL.

    Args:
        url (str): The URL of the image.
        question: An optional question to extract specific information about an image.

    Returns:
        str: The context of the image.
    """
    with dspy.context(lm=ModelManager.get_lm('gemini'), adapter=ModelManager.get_adapter()):
        describe = dspy.Predict(ImageContextExtractorSignature)
        result = describe(image=dspy.Image.from_url(url, download=True), question=question)
        return result.context