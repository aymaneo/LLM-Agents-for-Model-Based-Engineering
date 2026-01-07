"""EMF MCP Agent - A LangGraph-powered agent for EMF model manipulation."""

__version__ = "0.1.0"
__author__ = "EMF Agent Team"

from .stateless_agent import EMFStatelessAgent
from .mcp_client import MCPClient

__all__ = ["EMFStatelessAgent", "MCPClient", "__version__"]
