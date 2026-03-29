"""
Multi-city building compliance rule registry.
Each city contains room-type rules with minimum dimensions,
legal code references, and severity levels.

Room keys are matched via substring (rule_key.lower() in room_name.lower()),
so aliases like "Toilet", "Dining", "Sit Out" ensure OCR-parsed names find
the right rule.
"""

CITY_RULES = {
    "New Delhi": {
        "Guest": {
            "min_area_sqft": 95,
            "min_width_ft": 9.5,
            "code_reference": "Residential guidelines — Guest Room mapped to Bed Room standards.",
            "severity": "critical"
        },
        "Bedroom": {
            "min_area_sqft": 95,
            "min_width_ft": 9.5,
            "code_reference": "Delhi Building Bye-Laws 2016, Table 8.2 — Minimum size of rooms in residential buildings: Bed Room min 9.50 m² (≈95 sq ft), min width 2.4 m (≈7.9 ft, rounded to 9.5 ft for habitable comfort).",
            "severity": "critical"
        },
        "Living": {
            "min_area_sqft": 120,
            "min_width_ft": 10,
            "code_reference": "Delhi Building Bye-Laws 2016, Table 8.2 — Living/Drawing Room: min 12.0 m² (≈120 sq ft), min width 3.0 m (≈10 ft).",
            "severity": "critical"
        },
        "Drawing": {
            "min_area_sqft": 120,
            "min_width_ft": 10,
            "code_reference": "Delhi Building Bye-Laws 2016, Table 8.2 — Living/Drawing Room: min 12.0 m² (≈120 sq ft), min width 3.0 m (≈10 ft).",
            "severity": "critical"
        },
        "Dining": {
            "min_area_sqft": 100,
            "min_width_ft": 9,
            "code_reference": "Delhi Building Bye-Laws 2016, Table 8.2 — Dining / combined living-dining area.",
            "severity": "critical"
        },
        "Kitchen": {
            "min_area_sqft": 50,
            "min_width_ft": 7,
            "code_reference": "Delhi Building Bye-Laws 2016, Table 8.2 — Kitchen: min 5.0 m² (≈50 sq ft), min width 1.8 m (≈6 ft, rounded to 7 ft).",
            "severity": "critical"
        },
        "Toilet": {
            "min_area_sqft": 25,
            "min_width_ft": 5,
            "code_reference": "Delhi Building Bye-Laws 2016, Section 8.3 — Toilet/Bath/WC: min 2.8 m² (≈25 sq ft), min width 1.2 m (≈5 ft).",
            "severity": "warning"
        },
        "Washroom": {
            "min_area_sqft": 25,
            "min_width_ft": 5,
            "code_reference": "Delhi Building Bye-Laws 2016, Section 8.3 — Bath/WC: min 2.8 m² (≈25 sq ft), min width 1.2 m (≈5 ft).",
            "severity": "warning"
        },
        "Bath": {
            "min_area_sqft": 25,
            "min_width_ft": 5,
            "code_reference": "Delhi Building Bye-Laws 2016, Section 8.3 — Bath/WC: min 2.8 m² (≈25 sq ft), min width 1.2 m (≈5 ft).",
            "severity": "warning"
        },
        "WC": {
            "min_area_sqft": 16,
            "min_width_ft": 4,
            "code_reference": "Delhi Building Bye-Laws 2016, Section 8.3 — Water Closet (separate): min 1.5 m² (≈16 sq ft), min width 1.0 m (≈4 ft).",
            "severity": "warning"
        },
        "Powder": {
            "min_area_sqft": 16,
            "min_width_ft": 4,
            "code_reference": "Delhi Building Bye-Laws 2016, Section 8.3 — Powder Room / WC: min 1.5 m² (≈16 sq ft).",
            "severity": "warning"
        },
        "Sit Out": {
            "min_area_sqft": 0,
            "min_width_ft": 0,
            "code_reference": "Delhi Building Bye-Laws 2016 — Sit-out / Veranda / Balcony: no strict minimum for enclosed area.",
            "severity": "info"
        },
        "Veranda": {
            "min_area_sqft": 0,
            "min_width_ft": 0,
            "code_reference": "Delhi Building Bye-Laws 2016 — Veranda/Balcony: no strict minimum for enclosed area.",
            "severity": "info"
        },
        "Porch": {
            "min_area_sqft": 0,
            "min_width_ft": 3,
            "code_reference": "General Guidelines — Porch / Portico mapped to Sit Out standards.",
            "severity": "info"
        },
        "Balcony": {
            "min_area_sqft": 0,
            "min_width_ft": 0,
            "code_reference": "Delhi Building Bye-Laws 2016 — Veranda/Balcony: no strict minimum.",
            "severity": "info"
        },
        "Lift": {
            "min_area_sqft": 0,
            "min_width_ft": 0,
            "code_reference": "NBC 2016, Part 4 — Lift dimensions governed by IS 14665. Minimum car size depends on building occupancy.",
            "severity": "info"
        },
        "Stair": {
            "min_area_sqft": 0,
            "min_width_ft": 0,
            "code_reference": "Delhi Building Bye-Laws 2016 — Staircase width depends on building occupancy.",
            "severity": "info"
        },
        "Dress": {
            "min_area_sqft": 48,
            "min_width_ft": 6,
            "code_reference": "General Building Bye-Laws — Dressing Room: min 4.5 m² (≈48 sq ft).",
            "severity": "warning"
        },
        "Wash": {
            "min_area_sqft": 25,
            "min_width_ft": 5,
            "code_reference": "General Building Bye-Laws — Wash/Utility: min 2.8 m² (≈25 sq ft).",
            "severity": "warning"
        },
        "Pooja": {
            "min_area_sqft": 15,
            "min_width_ft": 3,
            "code_reference": "General Guidelines — Pooja / Prayer Room: typically min 1.5 m² (≈15 sq ft).",
            "severity": "info"
        },
        "Shaft": {
            "min_area_sqft": 16,
            "min_width_ft": 4,
            "code_reference": "General Building Bye-Laws — Ventilation Shaft: min 1.5 m² (≈16 sq ft).",
            "severity": "warning"
        },
        "Store": {
            "min_area_sqft": 32,
            "min_width_ft": 5,
            "code_reference": "General Building Bye-Laws — Store Room: min 3.0 m² (≈32 sq ft).",
            "severity": "warning"
        },
        "Parking": {
            "min_area_sqft": 135,
            "min_width_ft": 8,
            "code_reference": "General Building Bye-Laws — Parking (ECS): min 12.5 m² (≈135 sq ft) for one car.",
            "severity": "warning"
        },
        "Terrace": {
            "min_area_sqft": 0,
            "min_width_ft": 0,
            "code_reference": "General Guidelines — Terrace: no strict minimum area.",
            "severity": "info"
        },
        "Courtyard": {
            "min_area_sqft": 95,
            "min_width_ft": 10,
            "code_reference": "General Building Bye-Laws — Interior Courtyard: min 9.0 m² (≈95 sq ft).",
            "severity": "warning"
        },
        "Lounge": {
            "min_area_sqft": 100,
            "min_width_ft": 9,
            "code_reference": "General Guidelines — Lounge mapped to Living/Habitable room standards.",
            "severity": "critical"
        },
        "Parapet": {
            "min_area_sqft": 0,
            "min_width_ft": 0,
            "code_reference": "General Guidelines — Parapet is a safety barrier, typically min height 1.0 m.",
            "severity": "info"
        },
        "Canopy": {
            "min_area_sqft": 0,
            "min_width_ft": 0,
            "code_reference": "General Guidelines — Canopy: area not strictly regulated.",
            "severity": "info"
        }
    },

    "Mumbai": {
        "Guest": {
            "min_area_sqft": 95,
            "min_width_ft": 9.5,
            "code_reference": "Residential guidelines — Guest Room mapped to Bed Room standards.",
            "severity": "critical"
        },
        "Bedroom": {
            "min_area_sqft": 95,
            "min_width_ft": 9.5,
            "code_reference": "DCR Mumbai 2034, Regulation 36(3)(b) — Habitable room: min 9.5 m² (≈95 sq ft), min width 2.4 m (≈9.5 ft).",
            "severity": "critical"
        },
        "Living": {
            "min_area_sqft": 96,
            "min_width_ft": 10,
            "code_reference": "DCR Mumbai 2034, Regulation 36(3)(a) — Combined living/dining: min 9.6 m² (≈96 sq ft), min width 3.0 m (≈10 ft).",
            "severity": "critical"
        },
        "Drawing": {
            "min_area_sqft": 96,
            "min_width_ft": 10,
            "code_reference": "DCR Mumbai 2034, Regulation 36(3)(a) — Drawing / Living room.",
            "severity": "critical"
        },
        "Dining": {
            "min_area_sqft": 80,
            "min_width_ft": 8,
            "code_reference": "DCR Mumbai 2034, Regulation 36(3)(a) — Dining / combined living-dining area.",
            "severity": "critical"
        },
        "Kitchen": {
            "min_area_sqft": 50,
            "min_width_ft": 6,
            "code_reference": "DCR Mumbai 2034, Regulation 36(5) — Kitchen: min 4.5 m² (≈50 sq ft), min width 1.8 m (≈6 ft).",
            "severity": "critical"
        },
        "Toilet": {
            "min_area_sqft": 20,
            "min_width_ft": 4,
            "code_reference": "DCR Mumbai 2034, Regulation 36(7) — Toilet/Bathroom: min 1.8 m² (≈20 sq ft), min width 1.2 m (≈4 ft).",
            "severity": "warning"
        },
        "Washroom": {
            "min_area_sqft": 20,
            "min_width_ft": 4,
            "code_reference": "DCR Mumbai 2034, Regulation 36(7) — Bathroom: min 1.8 m² (≈20 sq ft), min width 1.2 m (≈4 ft).",
            "severity": "warning"
        },
        "Bath": {
            "min_area_sqft": 20,
            "min_width_ft": 4,
            "code_reference": "DCR Mumbai 2034, Regulation 36(7) — Bath: min 1.8 m² (≈20 sq ft).",
            "severity": "warning"
        },
        "WC": {
            "min_area_sqft": 12,
            "min_width_ft": 3.5,
            "code_reference": "DCR Mumbai 2034, Regulation 36(7) — WC: min 1.1 m² (≈12 sq ft), min width 1.0 m (≈3.5 ft).",
            "severity": "warning"
        },
        "Powder": {
            "min_area_sqft": 12,
            "min_width_ft": 3.5,
            "code_reference": "DCR Mumbai 2034, Regulation 36(7) — Powder Room / WC: min 1.1 m² (≈12 sq ft).",
            "severity": "warning"
        },
        "Sit Out": {
            "min_area_sqft": 0,
            "min_width_ft": 0,
            "code_reference": "DCR Mumbai 2034 — Sit-out / Balcony: no strict minimum.",
            "severity": "info"
        },
        "Veranda": {
            "min_area_sqft": 0,
            "min_width_ft": 0,
            "code_reference": "DCR Mumbai 2034 — Veranda/Balcony: no strict minimum.",
            "severity": "info"
        },
        "Stair": {
            "min_area_sqft": 0,
            "min_width_ft": 0,
            "code_reference": "DCR Mumbai 2034 — Staircase dimensions depend on building occupancy.",
            "severity": "info"
        },
        "Porch": {
            "min_area_sqft": 0,
            "min_width_ft": 3,
            "code_reference": "General Guidelines — Porch / Portico mapped to Sit Out standards.",
            "severity": "info"
        },
        "Balcony": {
            "min_area_sqft": 0,
            "min_width_ft": 0,
            "code_reference": "General Guidelines — Veranda/Balcony: no strict minimum.",
            "severity": "info"
        },
        "Lift": {
            "min_area_sqft": 0,
            "min_width_ft": 0,
            "code_reference": "NBC 2016 — Lift dimensions governed by IS 14665.",
            "severity": "info"
        },
        "Dress": {
            "min_area_sqft": 48,
            "min_width_ft": 6,
            "code_reference": "General Building Bye-Laws — Dressing Room: min 4.5 m² (≈48 sq ft).",
            "severity": "warning"
        },
        "Wash": {
            "min_area_sqft": 25,
            "min_width_ft": 5,
            "code_reference": "General Building Bye-Laws — Wash/Utility: min 2.8 m² (≈25 sq ft).",
            "severity": "warning"
        },
        "Pooja": {
            "min_area_sqft": 15,
            "min_width_ft": 3,
            "code_reference": "General Guidelines — Pooja / Prayer Room: typically min 1.5 m² (≈15 sq ft).",
            "severity": "info"
        },
        "Shaft": {
            "min_area_sqft": 16,
            "min_width_ft": 4,
            "code_reference": "General Building Bye-Laws — Ventilation Shaft: min 1.5 m² (≈16 sq ft).",
            "severity": "warning"
        },
        "Store": {
            "min_area_sqft": 32,
            "min_width_ft": 5,
            "code_reference": "General Building Bye-Laws — Store Room: min 3.0 m² (≈32 sq ft).",
            "severity": "warning"
        },
        "Parking": {
            "min_area_sqft": 135,
            "min_width_ft": 8,
            "code_reference": "General Building Bye-Laws — Parking (ECS): min 12.5 m² (≈135 sq ft) for one car.",
            "severity": "warning"
        },
        "Terrace": {
            "min_area_sqft": 0,
            "min_width_ft": 0,
            "code_reference": "General Guidelines — Terrace: no strict minimum area.",
            "severity": "info"
        },
        "Courtyard": {
            "min_area_sqft": 95,
            "min_width_ft": 10,
            "code_reference": "General Building Bye-Laws — Interior Courtyard: min 9.0 m² (≈95 sq ft).",
            "severity": "warning"
        },
        "Lounge": {
            "min_area_sqft": 100,
            "min_width_ft": 9,
            "code_reference": "General Guidelines — Lounge mapped to Living/Habitable room standards.",
            "severity": "critical"
        },
        "Parapet": {
            "min_area_sqft": 0,
            "min_width_ft": 0,
            "code_reference": "General Guidelines — Parapet is a safety barrier, typically min height 1.0 m.",
            "severity": "info"
        },
        "Canopy": {
            "min_area_sqft": 0,
            "min_width_ft": 0,
            "code_reference": "General Guidelines — Canopy: area not strictly regulated.",
            "severity": "info"
        }
    },

    "Bangalore": {
        "Guest": {
            "min_area_sqft": 95,
            "min_width_ft": 9.5,
            "code_reference": "Residential guidelines — Guest Room mapped to Bed Room standards.",
            "severity": "critical"
        },
        "Bedroom": {
            "min_area_sqft": 86,
            "min_width_ft": 9,
            "code_reference": "BDA Zoning Regulations 2017 / Karnataka Building Bye-Laws — Bedroom: min 8.0 m² (≈86 sq ft), min width 2.4 m (≈9 ft).",
            "severity": "critical"
        },
        "Living": {
            "min_area_sqft": 108,
            "min_width_ft": 10,
            "code_reference": "BDA Zoning Regulations 2017 — Living Room: min 10.0 m² (≈108 sq ft), min width 3.0 m (≈10 ft).",
            "severity": "critical"
        },
        "Drawing": {
            "min_area_sqft": 108,
            "min_width_ft": 10,
            "code_reference": "BDA Zoning Regulations 2017 — Drawing / Living Room.",
            "severity": "critical"
        },
        "Dining": {
            "min_area_sqft": 80,
            "min_width_ft": 8,
            "code_reference": "BDA Zoning Regulations 2017 — Dining / combined living-dining area.",
            "severity": "critical"
        },
        "Kitchen": {
            "min_area_sqft": 54,
            "min_width_ft": 6.5,
            "code_reference": "BDA Zoning Regulations 2017 — Kitchen: min 5.0 m² (≈54 sq ft), min width 2.0 m (≈6.5 ft).",
            "severity": "critical"
        },
        "Toilet": {
            "min_area_sqft": 20,
            "min_width_ft": 4,
            "code_reference": "BDA Zoning Regulations 2017 — Toilet/Bathroom/WC: min 1.8 m² (≈20 sq ft), min width 1.2 m (≈4 ft).",
            "severity": "warning"
        },
        "Washroom": {
            "min_area_sqft": 20,
            "min_width_ft": 4,
            "code_reference": "BDA Zoning Regulations 2017 — Bathroom/WC: min 1.8 m² (≈20 sq ft), min width 1.2 m (≈4 ft).",
            "severity": "warning"
        },
        "Bath": {
            "min_area_sqft": 20,
            "min_width_ft": 4,
            "code_reference": "BDA Zoning Regulations 2017 — Bath: min 1.8 m² (≈20 sq ft).",
            "severity": "warning"
        },
        "WC": {
            "min_area_sqft": 12,
            "min_width_ft": 3.5,
            "code_reference": "BDA Zoning Regulations 2017 — WC: min 1.1 m² (≈12 sq ft).",
            "severity": "warning"
        },
        "Powder": {
            "min_area_sqft": 12,
            "min_width_ft": 3.5,
            "code_reference": "BDA Zoning Regulations 2017 — Powder Room / WC: min 1.1 m² (≈12 sq ft).",
            "severity": "warning"
        },
        "Sit Out": {
            "min_area_sqft": 0,
            "min_width_ft": 0,
            "code_reference": "BDA Zoning Regulations 2017 — Sit-out / Balcony: no strict minimum.",
            "severity": "info"
        },
        "Veranda": {
            "min_area_sqft": 0,
            "min_width_ft": 0,
            "code_reference": "BDA Zoning Regulations 2017 — Veranda/Balcony: no strict minimum.",
            "severity": "info"
        },
        "Stair": {
            "min_area_sqft": 0,
            "min_width_ft": 0,
            "code_reference": "BDA Zoning Regulations 2017 — Staircase dimensions depend on building occupancy.",
            "severity": "info"
        },
        "Porch": {
            "min_area_sqft": 0,
            "min_width_ft": 3,
            "code_reference": "General Guidelines — Porch / Portico mapped to Sit Out standards.",
            "severity": "info"
        },
        "Balcony": {
            "min_area_sqft": 0,
            "min_width_ft": 0,
            "code_reference": "General Guidelines — Veranda/Balcony: no strict minimum.",
            "severity": "info"
        },
        "Lift": {
            "min_area_sqft": 0,
            "min_width_ft": 0,
            "code_reference": "NBC 2016 — Lift dimensions governed by IS 14665.",
            "severity": "info"
        },
        "Dress": {
            "min_area_sqft": 48,
            "min_width_ft": 6,
            "code_reference": "General Building Bye-Laws — Dressing Room: min 4.5 m² (≈48 sq ft).",
            "severity": "warning"
        },
        "Wash": {
            "min_area_sqft": 25,
            "min_width_ft": 5,
            "code_reference": "General Building Bye-Laws — Wash/Utility: min 2.8 m² (≈25 sq ft).",
            "severity": "warning"
        },
        "Pooja": {
            "min_area_sqft": 15,
            "min_width_ft": 3,
            "code_reference": "General Guidelines — Pooja / Prayer Room: typically min 1.5 m² (≈15 sq ft).",
            "severity": "info"
        },
        "Shaft": {
            "min_area_sqft": 16,
            "min_width_ft": 4,
            "code_reference": "General Building Bye-Laws — Ventilation Shaft: min 1.5 m² (≈16 sq ft).",
            "severity": "warning"
        },
        "Store": {
            "min_area_sqft": 32,
            "min_width_ft": 5,
            "code_reference": "General Building Bye-Laws — Store Room: min 3.0 m² (≈32 sq ft).",
            "severity": "warning"
        },
        "Parking": {
            "min_area_sqft": 135,
            "min_width_ft": 8,
            "code_reference": "General Building Bye-Laws — Parking (ECS): min 12.5 m² (≈135 sq ft) for one car.",
            "severity": "warning"
        },
        "Terrace": {
            "min_area_sqft": 0,
            "min_width_ft": 0,
            "code_reference": "General Guidelines — Terrace: no strict minimum area.",
            "severity": "info"
        },
        "Courtyard": {
            "min_area_sqft": 95,
            "min_width_ft": 10,
            "code_reference": "General Building Bye-Laws — Interior Courtyard: min 9.0 m² (≈95 sq ft).",
            "severity": "warning"
        },
        "Lounge": {
            "min_area_sqft": 100,
            "min_width_ft": 9,
            "code_reference": "General Guidelines — Lounge mapped to Living/Habitable room standards.",
            "severity": "critical"
        },
        "Parapet": {
            "min_area_sqft": 0,
            "min_width_ft": 0,
            "code_reference": "General Guidelines — Parapet is a safety barrier, typically min height 1.0 m.",
            "severity": "info"
        },
        "Canopy": {
            "min_area_sqft": 0,
            "min_width_ft": 0,
            "code_reference": "General Guidelines — Canopy: area not strictly regulated.",
            "severity": "info"
        }
    }
}

def get_available_cities() -> list[str]:
    """Returns a list of all city names with available rule sets."""
    return list(CITY_RULES.keys())

def get_rules_for_city(city: str) -> dict:
    """Returns the rule set for a given city, or empty dict if not found."""
    return CITY_RULES.get(city, {})
