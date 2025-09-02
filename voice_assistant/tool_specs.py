TOOL_SPECS = {
    "search_arxiv": {
        "description": "Search arXiv for a topic and return a short snippet.",
        "arguments": {"query": "string"},
        "required": ["query"]
    },
    "calculate": {
        "description": "Evaluate a mathematical expression using standard math syntax.",
        "arguments": {"expression": "string"},
        "required": ["expression"]
    },
    "get_weather": {
        "description": "Get the current weather for a given city/location.",
        "arguments": {"location": "string"},
        "required": []
    }
}