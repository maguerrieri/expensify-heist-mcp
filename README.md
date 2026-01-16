# Expensify Mail MCP Server

An MCP (Model Context Protocol) server that fetches Expensify CSV exports from Mail.app on macOS using AppleScript.

## Features

- **List Expensify emails** - Find all emails from Expensify with CSV attachments
- **Parse expense reports** - Extract structured expense data from CSV exports
- **YNAB integration** - Convert expenses to YNAB transaction format

## Requirements

- macOS (uses Mail.app via AppleScript)
- Python 3.11+
- Mail.app configured with your email account
- Expensify configured to email CSV exports

## Installation

```bash
cd expensify-mail-mcp
uv pip install -e .
```

Or with pip:

```bash
pip install -e .
```

## VS Code Setup

Add to your VS Code settings (`.vscode/settings.json` or user settings):

```json
{
  "mcp": {
    "servers": {
      "expensify-mail": {
        "command": "uv",
        "args": ["run", "--directory", "/path/to/expensify-mail-mcp", "expensify-mail-mcp"]
      }
    }
  }
}
```

Or if installed globally:

```json
{
  "mcp": {
    "servers": {
      "expensify-mail": {
        "command": "expensify-mail-mcp"
      }
    }
  }
}
```

## Permissions

On first run, macOS will ask for permission for your terminal/VS Code to control Mail.app. You'll need to allow this in:

**System Settings → Privacy & Security → Automation**

## Available Tools

### `expensify_list_emails`

List recent Expensify emails with CSV attachments.

**Input:**
- `limit` (optional): Maximum number of emails to return (default: 10)

**Output:** List of emails with message IDs, subjects, dates, and attachment names.

### `expensify_get_latest_report`

Get and parse the most recent Expensify CSV export.

**Output:** Parsed expenses with summary statistics.

### `expensify_get_report_by_id`

Get a specific Expensify report by email message ID.

**Input:**
- `message_id`: The Mail.app message ID

**Output:** Parsed expenses from that specific email.

### `expensify_get_ynab_transactions`

Convert Expensify expenses to YNAB transaction format.

**Input:**
- `account_id`: YNAB account ID for the transactions
- `message_id` (optional): Specific email to use; defaults to latest

**Output:** Transactions ready to import into YNAB.

## Workflow: Expensify → YNAB

1. **In Expensify:** Export a report as CSV (or set up scheduled email exports)
2. **In Mail.app:** The export email arrives
3. **Ask Copilot:** "Sync my latest Expensify report to YNAB"
4. **Copilot will:**
   - Call `expensify_get_ynab_transactions` to get formatted transactions
   - Call YNAB tools to create the transactions

## Setting Up Scheduled Exports in Expensify

1. Go to **Settings → Workspaces → [Your Workspace]**
2. Navigate to **Connections** or **Export**
3. Set up a scheduled export to email CSV files
4. Use your iCloud Mail address as the destination

## Troubleshooting

### "Mail wants to control..." permission denied
Go to System Settings → Privacy & Security → Automation and enable access.

### No emails found
- Make sure Mail.app has downloaded your emails (not just headers)
- Check that emails are from an address containing "expensify"
- Verify the emails have CSV attachments

### CSV parsing errors
The parser handles common Expensify export formats. If you have a custom export template, you may need to adjust the field mappings in `parser.py`.

## Development

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run directly
uv run expensify-mail-mcp
```
