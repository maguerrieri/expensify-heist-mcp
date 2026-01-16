"""MCP server that heists Expensify exports before bot detection catches us."""

import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .parser import parse_expensify_csv
from .heist import sync_login_interactive, sync_fetch_expenses_csv


# Create the MCP server
server = Server("expensify-heist-mcp")


def format_error(e: Exception) -> dict:
    """Format an exception into a user-friendly error dict."""
    error_str = str(e)
    
    if "Bot detection" in error_str or "Oops... an error has occurred" in error_str:
        return {
            "error": "Bot detection triggered",
            "message": "Expensify may have detected automation. Try clearing the session with: rm -rf ~/.expensify-session",
            "details": error_str,
        }
    
    if "Not logged in" in error_str:
        return {
            "error": "Not logged in",
            "message": "Please run expensify_login first to authenticate.",
        }
    
    if "Timeout" in error_str:
        return {
            "error": "Timeout",
            "message": "The operation timed out. The page may be loading slowly or the UI may have changed.",
            "details": error_str.split('\n')[0],
        }
    
    # Generic error
    return {"error": str(e)}


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="expensify_login",
            description="Open a browser window to log in to Expensify. Required before using other expensify_web_* tools. The browser will open and you'll have 2 minutes to complete login.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="expensify_web_export",
            description="Export expenses from Expensify via web browser. Requires being logged in (use expensify_login first). Returns parsed expense data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "report_id": {
                        "type": "string",
                        "description": "Optional: specific report ID to export. If not provided, exports current/unreported expenses.",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds for the browser operation. Default is 60.",
                    },
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    
    if name == "expensify_login":
        try:
            success = sync_login_interactive(timeout_seconds=120)
            if success:
                return [TextContent(
                    type="text",
                    text=json.dumps({"status": "success", "message": "Successfully logged in to Expensify"}),
                )]
            else:
                return [TextContent(
                    type="text",
                    text=json.dumps({"status": "timeout", "message": "Login timed out. Please try again."}),
                )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps(format_error(e), indent=2),
            )]
    
    elif name == "expensify_web_export":
        report_id = arguments.get("report_id")
        timeout = arguments.get("timeout", 60)
        try:
            csv_content, report_name = sync_fetch_expenses_csv(report_id=report_id, headless=False, timeout=timeout)
            expenses = parse_expensify_csv(csv_content)
            result = {
                "report_name": report_name,
                "expenses": [e.to_dict() for e in expenses],
                "summary": {
                    "total_expenses": len(expenses),
                    "total_amount": str(sum(e.amount for e in expenses)),
                    "currencies": list(set(e.currency for e in expenses)),
                    "categories": list(set(e.category for e in expenses if e.category)),
                },
            }
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2),
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps(format_error(e), indent=2),
            )]
    
    return [TextContent(
        type="text",
        text=json.dumps({"error": f"Unknown tool: {name}"}),
    )]


async def run_server():
    """Run the MCP server with stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main():
    """Entry point for the MCP server."""
    import asyncio
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
