"""Socrates - AI coding agent that works with any LLM."""

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

__version__ = "0.1.0"

from socrates.agent import Agent as Agent
from socrates.llm import LLMClient as LLMClient
from socrates.config import Config as Config
