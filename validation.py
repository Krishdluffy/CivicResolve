"""Input validation helpers for CivicResolve."""

from __future__ import annotations

import re
from typing import Any

CATEGORIES = [
    "Pothole / Road Damage",
    "Garbage / Waste",
    "Streetlight",
    "Water Leakage",
    "Drainage / Flooding",
    "Public Safety",
    "Other",
]

PRIORITIES = ["Low", "Medium", "High"]
STATUSES = ["Reported", "Under Review", "In Progress", "Resolved", "Rejected"]
DEPARTMENTS = [
    "Public Works",
    "Sanitation",
    "Electrical",
    "Water Supply",
    "Public Safety",
    "Other",
]

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def validate_email(email: str) -> str:
    """Return a normalized email address or raise ValueError."""
    normalized = email.strip().lower()
    if len(normalized) > 254 or not EMAIL_PATTERN.fullmatch(normalized):
        raise ValueError("Enter a valid email address, such as name@example.com.")
    return normalized


def validate_person(name: str, email: str) -> tuple[str, str]:
    clean_name = " ".join(name.split())
    if not 2 <= len(clean_name) <= 80:
        raise ValueError("Name must contain between 2 and 80 characters.")
    return clean_name, validate_email(email)


def validate_report(data: dict[str, Any]) -> dict[str, Any]:
    """Validate report fields before sending them to MongoDB."""
    title = " ".join(str(data.get("title", "")).split())
    description = str(data.get("description", "")).strip()
    category = str(data.get("category", "")).strip()
    priority = str(data.get("priority", "")).strip()
    area = " ".join(str(data.get("area", "")).split())
    landmark = " ".join(str(data.get("landmark", "")).split()) or "Not specified"

    if not 5 <= len(title) <= 100:
        raise ValueError("The title must contain between 5 and 100 characters.")
    if not 15 <= len(description) <= 2000:
        raise ValueError("The description must contain between 15 and 2,000 characters.")
    if category not in CATEGORIES:
        raise ValueError("Choose a valid issue category.")
    if priority not in PRIORITIES:
        raise ValueError("Choose a valid priority.")
    if not 2 <= len(area) <= 100:
        raise ValueError("Area must contain between 2 and 100 characters.")
    if len(landmark) > 150:
        raise ValueError("Landmark must be 150 characters or fewer.")

    return {
        "title": title,
        "description": description,
        "category": category,
        "priority": priority,
        "area": area,
        "landmark": landmark,
    }


def choose_department(category: str) -> str:
    mapping = {
        "Pothole / Road Damage": "Public Works",
        "Garbage / Waste": "Sanitation",
        "Streetlight": "Electrical",
        "Water Leakage": "Water Supply",
        "Drainage / Flooding": "Public Works",
        "Public Safety": "Public Safety",
    }
    return mapping.get(category, "Other")
