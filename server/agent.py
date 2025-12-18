import os
from dataclasses import dataclass

from google.adk.agents import Agent
from google.adk.tools import google_search
from instructions import SYSTEM_INSTRUCTION
from tools.ui_tools import display_card, display_content, display_list


@dataclass
class AgentConfig:
    """Configuration for the Navigo AI Agent."""

    model: str = os.environ.get("MODEL", "gemini-live-2.5-flash-native-audio")
    voice_name: str = os.environ.get("VOICE_NAME", "Puck")
    instruction: str = SYSTEM_INSTRUCTION
    use_vertex_ai: bool = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "FALSE").upper() == "TRUE"
    project_id: str = os.environ.get("PROJECT_ID")
    location: str = os.environ.get("LOCATION")


# Default configuration instance
_DEFAULT_CONFIG = AgentConfig()
VOICE_NAME = _DEFAULT_CONFIG.voice_name


def create_agent(config: AgentConfig = None) -> Agent:
    """
    Creates a Google ADK Agent based on the provided configuration.

    Args:
        config: AgentConfig instance. If None, uses default configuration.
    """
    cfg = config or _DEFAULT_CONFIG
    return Agent(
        name="voice_assistant_agent",
        model=cfg.model,
        instruction=cfg.instruction,
        tools=[
            google_search,
            display_content,
            display_card,
            display_list,
        ],
    )
