import os
from linkup import LinkupClient
from .tools_manager import tool

# Only register the tool if API key exists
linkup_api_key = os.getenv("LINKUP_API_KEY")

if not linkup_api_key:
    print("LINKUP_API_KEY not set, search tool will not be available. You can get one from https://www.linkup.so/")
else:
    client = LinkupClient(api_key=linkup_api_key)
    
    @tool
    def search(query: str):
        """
        Search for a query on the internet. Use this tool to find recent information or data that is not available in the current context.
        """
        results = client.search(query, depth="standard", output_type="sourcedAnswer")
        return results