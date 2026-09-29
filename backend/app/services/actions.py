"""Rule-based action recommendation engine.

Generates role-specific, ward-level and city-level actions based on the risk
level, the risk causes and the resources available. Every action carries a
responsible department, priority (Immediate/Today/Monitor), reason and status.
"""
from ..models import Ward

# level -> list of (category, title, department, priority)
ACTIONS_BY_LEVEL = {
    "green": [
        ("Monitoring", "Continue routine heat surveillance", "Municipal Corporation", "Monitor"),
        ("Monitoring", "Keep drinking-water points stocked", "Water Supply Department", "Monitor"),
    ],
    "yellow": [
        ("Public awareness", "Start public hydration awareness messages", "Information & Publicity", "Today"),
        ("Monitoring", "Monitor elderly and chronic-disease residents", "Urban Health", "Monitor"),
        ("Infrastructure", "Check drinking-water facilities", "Water Supply Department", "Today"),
        ("Health", "Monitor primary health-centre supplies", "Health Department", "Monitor"),
    ],
    "orange": [
        ("Health", "Extend primary health-centre hours", "Health Department", "Today"),
        ("Health", "Prepare ORS, IV fluids and emergency medicines", "Health Department", "Immediate"),
        ("Labour", "Begin outdoor-worker welfare checks", "Labour Department", "Today"),
        ("Public awareness", "Send precautionary SMS alerts", "Information & Publicity", "Today"),
        ("Infrastructure", "Deploy additional drinking-water points", "Water Supply Department", "Today"),
    ],
    "red": [
        ("Infrastructure", "Open cooling centres", "Municipal Corporation", "Immediate"),
        ("Labour", "Shift outdoor work to 6 AM-10 AM and after 4 PM", "Labour Department", "Immediate"),
        ("Health", "Activate hospital surge planning", "Health Department", "Immediate"),
        ("Infrastructure", "Deploy mobile water and ORS units", "Water Supply Department", "Immediate"),
        ("Social welfare", "Contact elderly-care volunteers", "Social Welfare Department", "Today"),
        ("Health", "Increase emergency and ambulance staffing", "Health Department", "Today"),
        ("Public awareness", "Issue multilingual ward alerts", "Information & Publicity", "Immediate"),
    ],
    "maroon": [
        ("Command", "Activate city heat-emergency protocol", "Municipal Commissioner", "Immediate"),
        ("Infrastructure", "Keep cooling centres open for extended hours", "Municipal Corporation", "Immediate"),
        ("Labour", "Suspend non-essential outdoor work during peak hours", "Labour Department", "Immediate"),
        ("Social welfare", "Send mobile outreach teams to informal settlements", "Social Welfare Department", "Immediate"),
        ("Infrastructure", "Ensure electricity and water supply to cooling centres", "Electricity & Water Boards", "Immediate"),
        ("Public awareness", "Repeatedly issue multilingual alerts", "Information & Publicity", "Immediate"),
        ("Health", "Coordinate hospital beds, ambulance routes and emergency supplies", "Health Department", "Immediate"),
    ],
}

DEPARTMENT_BY_LEVEL = {
    "yellow": "Municipal Corporation",
    "orange": "Municipal Corporation",
    "red": "Municipal Corporation",
    "maroon": "Municipal Commissioner",
}


def generate_ward_actions(ward: Ward, risk_level: str, context: dict | None = None) -> list:
    """Actions for one ward, with reasons derived from the ward's situation."""
    context = context or {}
    level = risk_level if risk_level in ACTIONS_BY_LEVEL else "green"
    actions = []
    for category, title, department, priority in ACTIONS_BY_LEVEL[level]:
        reason = _reason_for(level, category, ward, context)
        actions.append({
            "ward_id": ward.id,
            "ward_code": ward.code,
            "ward_name": ward.name,
            "risk_level": level,
            "category": category,
            "title": title,
            "department": department,
            "priority": priority,
            "reason": reason,
            "status": "Pending",
        })
    return actions


def generate_city_actions(city_risk_level: str, context: dict | None = None) -> list:
    """City-wide coordination actions: the full action library for the city's
    risk level, flagged as city-wide so role views can filter by department."""
    context = context or {}
    level = city_risk_level if city_risk_level in ACTIONS_BY_LEVEL else "green"
    label = {"green": "Low", "yellow": "Moderate", "orange": "High",
             "red": "Very High", "maroon": "Extreme"}[level]
    actions = []
    for category, title, department, priority in ACTIONS_BY_LEVEL[level]:
        actions.append({
            "ward_id": None,
            "ward_code": "CITY",
            "ward_name": "City-wide",
            "risk_level": level,
            "category": category,
            "title": title,
            "department": department,
            "priority": priority,
            "reason": f"City risk is {label}; applies across all wards.",
            "status": "Pending",
        })
    return actions


def _reason_for(level: str, category: str, ward: Ward, ctx: dict) -> str:
    vuln = ctx.get("vulnerability", {})
    top = ""
    if vuln and vuln.get("contributions"):
        top = max(vuln["contributions"].items(), key=lambda kv: kv[1])
        top = f" Top vulnerability factor: {top[0].replace('_', ' ')}."
    why = {
        ("yellow", "Health"): "Primary health centres report normal load but heat risk is rising.",
        ("orange", "Health"): "Ward is under High heat risk; PHC supply buffers should be topped up.",
        ("red", "Health"): "Red risk + vulnerable population => surge planning required.",
        ("maroon", "Health"): "Extreme risk: hospital beds, ambulances and supplies must be coordinated.",
        ("red", "Labour"): "Outdoor workers face dangerous WBGT during peak hours.",
        ("maroon", "Labour"): "Extreme risk: outdoor work is unsafe during the afternoon.",
        ("maroon", "Social welfare"): "Informal settlements in this ward have the highest exposure.",
        ("red", "Social welfare"): "Elderly residents need proactive checks during the heat episode.",
    }.get((level, category), f"Risk level is {level}; action applies to protect residents.")
    return why + top


def recommended_city_actions(level: str, summary: dict) -> list:
    """Short headline recommendations for the dashboard."""
    by_level = {
        "green": [("Maintain routine surveillance", "Municipal Corporation", "Monitor")],
        "yellow": [("Issue hydration advisory", "Information & Publicity", "Today"),
                   ("Audit water points and PHC stocks", "Health Department", "Today")],
        "orange": [("Extend PHC hours and stock ORS/IV fluids", "Health Department", "Today"),
                   ("Deploy extra water points", "Water Supply Department", "Today"),
                   ("Start outdoor-worker checks", "Labour Department", "Today")],
        "red": [("Open cooling centres", "Municipal Corporation", "Immediate"),
                ("Shift outdoor work to morning/evening", "Labour Department", "Immediate"),
                ("Activate hospital surge planning", "Health Department", "Immediate")],
        "maroon": [("Activate city heat-emergency protocol", "Municipal Commissioner", "Immediate"),
                   ("Coordinate beds, ambulances and supplies", "Health Department", "Immediate")],
    }
    return [
        {"title": t, "department": d, "priority": p}
        for t, d, p in by_level.get(level, by_level["green"])
    ]