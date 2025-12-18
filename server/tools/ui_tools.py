"""
UI tools for displaying content to users alongside voice interactions.

These tools allow the agent to send structured content (cards, lists, formatted text)
to the client UI while maintaining voice-first interaction.
"""
import asyncio
import json
from typing import List, Optional

from context import get_session_handler


def display_content(content: str, title: str = "Information") -> str:
    """
    Displays text content to the user on their screen.

    Use this tool when you want to show detailed information, explanations,
    or formatted text while you speak. The content will appear in a dedicated
    UI area separate from the voice transcript.

    Args:
        content: The main text content to display
        title: Optional title for the content block

    Returns:
        Confirmation message for the model
    """
    handler = get_session_handler()
    if not handler or not handler.websocket:
        return "Error: Could not display content (No active connection)."

    try:
        # Create the message payload
        data = {
            "title": title,
            "content": content,
        }

        # Send message asynchronously
        message = json.dumps({"type": "ui_content", "data": data})
        # Use create_task to handle async WebSocket send from sync context
        # Tools are called within an async context, so get_running_loop should work
        loop = asyncio.get_running_loop()
        loop.create_task(handler.websocket.send(message))
        return f"Content '{title}' has been displayed to the user."
    except Exception as e:
        return f"Error displaying content: {str(e)}"


def display_card(title: str, content: str, footer: Optional[str] = None) -> str:
    """
    Displays a structured card component to the user.

    Use this tool for presenting information in a card format with a title,
    main content, and optional footer. Ideal for itineraries, summaries,
    or highlighted information.

    Args:
        title: The card title
        content: The main card content
        footer: Optional footer text

    Returns:
        Confirmation message for the model
    """
    handler = get_session_handler()
    if not handler or not handler.websocket:
        return "Error: Could not display card (No active connection)."

    try:
        # Create the message payload
        data = {
            "title": title,
            "content": content,
        }
        if footer:
            data["footer"] = footer

        # Send message asynchronously
        message = json.dumps({"type": "ui_card", "data": data})
        loop = asyncio.get_running_loop()
        loop.create_task(handler.websocket.send(message))
        return f"Card '{title}' has been displayed to the user."
    except Exception as e:
        return f"Error displaying card: {str(e)}"


def display_list(items: List[str], title: str = "List") -> str:
    """
    Displays a formatted list to the user.

    Use this tool to show lists of items, such as travel destinations,
    recommendations, or step-by-step instructions.

    Args:
        items: List of strings to display as list items
        title: Optional title for the list

    Returns:
        Confirmation message for the model
    """
    handler = get_session_handler()
    if not handler or not handler.websocket:
        return "Error: Could not display list (No active connection)."

    try:
        # Ensure items is a list of strings
        if not isinstance(items, list):
            return "Error: items must be a list of strings."

        # Create the message payload
        data = {
            "title": title,
            "items": items,
        }

        # Send message asynchronously
        message = json.dumps({"type": "ui_list", "data": data})
        loop = asyncio.get_running_loop()
        loop.create_task(handler.websocket.send(message))
        return f"List '{title}' with {len(items)} items has been displayed to the user."
    except Exception as e:
        return f"Error displaying list: {str(e)}"
