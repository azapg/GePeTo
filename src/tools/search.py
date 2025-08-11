import os
from linkup import LinkupClient
from .tools_manager import tool

client = LinkupClient(api_key=os.getenv("LINKUP_API_KEY"))

@tool
def search(query: str):
    """
    Search for a query on the internet.
    """
    results = client.search(query, depth="standard", output_type="sourcedAnswer")
    return results