import json
from datetime import datetime, timedelta


RULE_CERTIFICATION = "required certification"
RULE_OVERLAP = "overlap"
RULE_REST = "11-hour rest"
RULE_WEEKLY_HOURS = "40-hour weekly limit"


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value)


def week_start(value: str) -> datetime:
    date = parse_time(value)
    return datetime.combine(date.date() - timedelta(days=date.weekday()), datetime.min.time())


def duration_hours(shift: dict) -> float:
    return (parse_time(shift["end"]) - parse_time(shift["start"])).total_seconds() / 3600


def overlaps(first: dict, second: dict) -> bool:
    return (
        parse_time(first["start"]) < parse_time(second["end"])
        and parse_time(second["start"]) < parse_time(first["end"])
    )


def validate_claim(claimer: dict, target: dict, assigned_shifts: list[dict]) -> list[dict]:
    reasons: list[dict] = []
    required = target.get("required_certification")
    certifications = json.loads(claimer["certifications_json"]) if isinstance(
        claimer.get("certifications_json"), str
    ) else claimer.get("certifications", [])
    if required and required not in certifications:
        reasons.append(
            {
                "rule": RULE_CERTIFICATION,
                "message": (
                    f"{claimer['name']} does not have the required "
                    f"{required} certification for {target['id']}."
                ),
                "conflicting_shift": target["id"],
            }
        )

    same_week = [
        shift for shift in assigned_shifts
        if week_start(shift["start"]) == week_start(target["start"])
    ]
    for shift in same_week:
        if overlaps(target, shift):
            reasons.append(
                {
                    "rule": RULE_OVERLAP,
                    "message": f"{target['id']} overlaps with assigned shift {shift['id']}.",
                    "conflicting_shift": shift["id"],
                }
            )

    for shift in same_week:
        if overlaps(target, shift):
            continue
        if parse_time(target["end"]) <= parse_time(shift["start"]):
            gap_hours = (parse_time(shift["start"]) - parse_time(target["end"])).total_seconds() / 3600
        elif parse_time(shift["end"]) <= parse_time(target["start"]):
            gap_hours = (parse_time(target["start"]) - parse_time(shift["end"])).total_seconds() / 3600
        else:
            continue
        if gap_hours < 11:
            reasons.append(
                {
                    "rule": RULE_REST,
                    "message": (
                        f"{target['id']} leaves {gap_hours:g} hours before/after "
                        f"assigned shift {shift['id']}; at least 11 hours are required."
                    ),
                    "conflicting_shift": shift["id"],
                }
            )

    weekly_hours = sum(duration_hours(shift) for shift in same_week) + duration_hours(target)
    if weekly_hours > 40:
        reasons.append(
            {
                "rule": RULE_WEEKLY_HOURS,
                "message": (
                    f"Claiming {target['id']} would give {claimer['name']} "
                    f"{weekly_hours:g} assigned hours in that week; the limit is 40."
                ),
                "conflicting_shift": target["id"],
            }
        )
    return reasons
