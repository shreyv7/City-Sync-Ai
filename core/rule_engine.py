"""
Enhanced deterministic rule engine with multi-city support,
code references, severity tagging, and actionable fix suggestions.
"""

from data.city_rules import get_rules_for_city


def _generate_fix(room_name: str, area: float, min_area: float,
                  effective_width: float, min_width: float,
                  width: float, length: float) -> str:
    """Generates a human-readable fix suggestion for a failing room."""
    fixes = []

    if min_area and area < min_area:
        deficit = min_area - area
        # Suggest proportional increase
        if width > 0 and length > 0:
            extra_length = deficit / width
            fixes.append(
                f"Increase length by ~{extra_length:.1f} ft (to {length + extra_length:.1f} ft) "
                f"to meet the minimum {min_area} sq ft area requirement."
            )
        else:
            fixes.append(f"Increase area by {deficit:.1f} sq ft to meet {min_area} sq ft.")

    if min_width and effective_width < min_width:
        gap = min_width - effective_width
        fixes.append(
            f"Increase the narrower dimension by {gap:.1f} ft "
            f"(from {effective_width:.1f} ft to {min_width:.1f} ft) to meet the minimum width."
        )

    return " | ".join(fixes) if fixes else ""


def calculate_compliance(rooms_data: list[dict], city: str = "New Delhi") -> list[dict]:
    """
    Calculates area and checks compliance against city-specific rules.

    Args:
        rooms_data: List of room dicts with room_name, width_ft, length_ft.
        city: The city whose rules to evaluate against.

    Returns:
        List of enriched result dicts per room.
    """
    city_rules = get_rules_for_city(city)
    results = []

    for room in rooms_data:
        name = room.get("room_name", "Unknown")
        width = room.get("width_ft", 0) or 0
        length = room.get("length_ft", 0) or 0
        area = round(width * length, 2)

        result = {
            "room_name": name,
            "width_ft": width,
            "length_ft": length,
            "area_sqft": area,
            "required_area_sqft": None,
            "status": "NOT_APPLICABLE",
            "severity": "info",
            "reason": "",
            "code_reference": "",
            "suggested_fix": ""
        }

        # Match room name to a rule key
        matched_rule = None
        for rule_key, rules in city_rules.items():
            if rule_key.lower() in name.lower():
                matched_rule = rules
                break

        if matched_rule:
            min_area = matched_rule.get("min_area_sqft", 0)
            min_width = matched_rule.get("min_width_ft", 0)
            result["required_area_sqft"] = min_area
            result["severity"] = matched_rule.get("severity", "info")
            result["code_reference"] = matched_rule.get("code_reference", "")

            if width == 0 or length == 0:
                result["status"] = "INSUFFICIENT_DATA"
                result["reason"] = "Dimensions missing"
            else:
                failure_reasons = []
                effective_width = min(width, length)

                if min_area and area < min_area:
                    failure_reasons.append(
                        f"Area {area:.1f} sq ft < Minimum {min_area} sq ft"
                    )
                if min_width and effective_width < min_width:
                    failure_reasons.append(
                        f"Width {effective_width:.1f} ft < Minimum {min_width} ft"
                    )

                if failure_reasons:
                    result["status"] = "FAIL"
                    result["reason"] = "; ".join(failure_reasons)
                    result["suggested_fix"] = _generate_fix(
                        name, area, min_area, effective_width, min_width, width, length
                    )
                else:
                    result["status"] = "PASS"
                    result["reason"] = "Compliant"

        results.append(result)

    return results
