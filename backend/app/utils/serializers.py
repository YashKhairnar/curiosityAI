import json
import re

def serialize_claude_text(message):
    """Extract text content from Claude message"""
    if not message or not message.content:
        return None
    
    # Get first text block
    for block in message.content:
        if hasattr(block, 'text'):
            return block.text.strip()
    
    return None


