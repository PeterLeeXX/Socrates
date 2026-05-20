"""Base class for all tools."""

from abc import ABC, abstractmethod


class BaseTool(ABC):
    """Every tool must define name, description, parameters, and execute()."""

    name: str = ""
    description: str = ""
    parameters: dict = {}  # JSON Schema for the parameters

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Run the tool and return a string result."""
        ...

    def to_schema(self) -> dict:
        """Convert to OpenAI function-calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
