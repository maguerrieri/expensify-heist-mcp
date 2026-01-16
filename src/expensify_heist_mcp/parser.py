"""Parse Expensify CSV exports into structured data."""

import csv
import io
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class Expense:
    """A single expense from an Expensify report."""

    date: datetime
    merchant: str
    amount: Decimal
    currency: str
    category: str
    tag: str | None
    description: str | None
    report_name: str | None
    reimbursable: bool
    billable: bool
    receipt_url: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "date": self.date.isoformat(),
            "merchant": self.merchant,
            "amount": str(self.amount),
            "currency": self.currency,
            "category": self.category,
            "tag": self.tag,
            "description": self.description,
            "report_name": self.report_name,
            "reimbursable": self.reimbursable,
            "billable": self.billable,
            "receipt_url": self.receipt_url,
        }


def parse_expensify_csv(csv_content: str) -> list[Expense]:
    """Parse Expensify CSV export into Expense objects.
    
    Expensify CSVs can have varying column names depending on export settings.
    This parser handles the common formats.
    """
    reader = csv.DictReader(io.StringIO(csv_content))
    
    # Normalize field names (Expensify uses various naming conventions)
    field_mapping = {
        # Date fields
        "date": ["Timestamp", "Date", "Created", "Transaction Date", "Expense Date"],
        # Merchant fields
        "merchant": ["Merchant", "Vendor", "Payee", "Description"],
        # Amount fields
        "amount": ["Amount", "Total", "Expense Amount"],
        # Currency fields
        "currency": ["Currency", "Original Currency"],
        # Category fields
        "category": ["Category", "Expense Category", "GL Code"],
        # Tag fields
        "tag": ["Tag", "Tags", "Project", "Cost Center"],
        # Description/comment fields
        "description": ["Comment", "Description", "Notes", "Memo"],
        # Report fields
        "report_name": ["Report Name", "Report", "Report Title"],
        # Reimbursable
        "reimbursable": ["Reimbursable", "Is Reimbursable"],
        # Billable
        "billable": ["Billable", "Is Billable"],
        # Receipt
        "receipt_url": ["Receipt URL", "Receipt", "Receipt Link"],
    }
    
    def find_field(row: dict, field_names: list[str]) -> str | None:
        """Find a field value using possible column names."""
        for name in field_names:
            if name in row:
                return row[name]
            # Try case-insensitive match
            for key in row:
                if key.lower() == name.lower():
                    return row[key]
        return None
    
    def parse_date(date_str: str | None) -> datetime:
        """Parse various date formats."""
        if not date_str:
            return datetime.now()
        
        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m/%d/%y",
            "%d/%m/%Y",
            "%d/%m/%y",
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%B %d, %Y",
            "%b %d, %Y",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        return datetime.now()
    
    def parse_amount(amount_str: str | None) -> Decimal:
        """Parse amount string to Decimal."""
        if not amount_str:
            return Decimal("0")
        
        # Remove currency symbols and whitespace
        cleaned = amount_str.strip()
        for char in "$€£¥,":
            cleaned = cleaned.replace(char, "")
        
        # Handle parentheses for negative numbers
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = "-" + cleaned[1:-1]
        
        try:
            return Decimal(cleaned)
        except Exception:
            return Decimal("0")
    
    def parse_bool(value: str | None) -> bool:
        """Parse boolean from various string representations."""
        if not value:
            return False
        return value.lower() in ("yes", "true", "1", "y")
    
    expenses = []
    
    for row in reader:
        expense = Expense(
            date=parse_date(find_field(row, field_mapping["date"])),
            merchant=find_field(row, field_mapping["merchant"]) or "Unknown",
            amount=parse_amount(find_field(row, field_mapping["amount"])),
            currency=find_field(row, field_mapping["currency"]) or "USD",
            category=find_field(row, field_mapping["category"]) or "",
            tag=find_field(row, field_mapping["tag"]),
            description=find_field(row, field_mapping["description"]),
            report_name=find_field(row, field_mapping["report_name"]),
            reimbursable=parse_bool(find_field(row, field_mapping["reimbursable"])),
            billable=parse_bool(find_field(row, field_mapping["billable"])),
            receipt_url=find_field(row, field_mapping["receipt_url"]),
        )
        expenses.append(expense)
    
    return expenses
