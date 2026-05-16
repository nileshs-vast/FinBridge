from __future__ import annotations

# Payment-head tree definitions per business type.
# Each item: {"name": str, "children": [{"name": str}]}
TEMPLATES: dict[str, list[dict]] = {
    "manufacturing": [
        {
            "name": "Raw Materials",
            "children": [{"name": "Steel"}, {"name": "Plastic"}],
        },
        {
            "name": "Utilities",
            "children": [{"name": "Electricity"}, {"name": "Water"}],
        },
        {
            "name": "Logistics",
            "children": [{"name": "Transport"}, {"name": "Warehousing"}],
        },
    ],
    "it": [
        {
            "name": "Salaries",
            "children": [{"name": "Engineering"}, {"name": "Operations"}],
        },
        {
            "name": "Infrastructure",
            "children": [{"name": "Cloud"}, {"name": "Software Licenses"}],
        },
        {
            "name": "Office",
            "children": [{"name": "Rent"}, {"name": "Internet"}],
        },
    ],
    "services": [
        {
            "name": "Salaries",
            "children": [{"name": "Consultants"}, {"name": "Admin"}],
        },
        {
            "name": "Travel",
            "children": [{"name": "Local"}, {"name": "International"}],
        },
        {
            "name": "Marketing",
            "children": [{"name": "Digital"}, {"name": "Events"}],
        },
    ],
}
