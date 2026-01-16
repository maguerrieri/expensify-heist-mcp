"""MCP server that heists Expensify exports via Safari JS injection."""

import sys

if sys.platform != "darwin":
    raise RuntimeError(
        "expensify-heist-mcp only works on macOS. "
        "It uses Safari and AppleScript for automation."
    )

__version__ = "0.1.0"
