from collections import Counter, defaultdict
from statistics import mean

from .schemas import (
    ConflictRecord,
    ConstraintRule,
    EmergencyRescheduleRequest,
    EmergencyRescheduleResponse,
    QualityResponse,
    SimulationRequest,
    SimulationResponse,
    SuggestionRecord,
    SuggestionResponse,
    TimetableEntry,
)


def detect_conflicts(timetable: list[TimetableEntry]) -> list[ConflictRecord]:
    conflicts: list[ConflictRecord] = []
    faculty_map: dict[tuple[str, str, int], list[TimetableEntry]] = defaultdict(list)
    room_map: dict[tuple[str, int], list[TimetableEntry]] = defaultdict(list)
    section_map: dict[tuple[str, str, int], list[TimetableEntry]] = defaultdict(list)

    for entry in timetable:
        faculty_map[(entry.faculty_id, entry.day, entry.period)].append(entry)
        room_map[(entry.room, entry.period)].append(entry)
        section_map[(entry.section, entry.day, entry.period)].append(entry)

    for (_, day, period), entries in faculty_map.items():
        if len(entries) > 1:
            for entry in entries:
                conflicts.append(
                    ConflictRecord(
                        conflict_type="FACULTY",
                        message=f"Faculty {entry.faculty_id} has multiple classes at same slot",
                        section=entry.section,
                        day=day,
                        period=period,
                    )
                )

    for (_, period), entries in room_map.items():
        if len(entries) > 1:
            for entry in entries:
                conflicts.append(
                    ConflictRecord(
                        conflict_type="ROOM",
                        message=f"Room {entry.room} double-booked at period {period}",
                        section=entry.section,
                        day=entry.day,
                        period=period,
                    )
                )

    for (_, day, period), entries in section_map.items():
        if len(entries) > 1:
            for entry in entries:
                conflicts.append(
                    ConflictRecord(
                        conflict_type="SECTION",
                        message=f"Section {entry.section} has overlap at period {period}",
                        section=entry.section,
                        day=day,
                        period=period,
                    )
                )

    return conflicts


def calculate_quality(tenant_id: str, timetable: list[TimetableEntry], conflicts_count: int) -> QualityResponse:
    faculty_load_counter = Counter(entry.faculty_id for entry in timetable)
    room_counter = Counter(entry.room for entry in timetable)

    if faculty_load_counter:
        loads = list(faculty_load_counter.values())
        avg_load = mean(loads)
        imbalance = sum(abs(load - avg_load) for load in loads) / len(loads)
        faculty_load_balance = max(0.0, 100 - imbalance * 10)
    else:
        faculty_load_balance = 100.0

    student_fatigue = max(0.0, 100 - len([e for e in timetable if e.period >= 6]) * 2)

    if room_counter:
        room_utilization = min(100.0, mean(room_counter.values()) * 20)
    else:
        room_utilization = 0.0

    clash_risk = max(0.0, 100 - conflicts_count * 20)

    overall_quality = round(
        (faculty_load_balance * 0.3)
        + (student_fatigue * 0.25)
        + (room_utilization * 0.2)
        + (clash_risk * 0.25),
        2,
    )

    return QualityResponse(
        tenant_id=tenant_id,
        faculty_load_balance=round(faculty_load_balance, 2),
        student_fatigue=round(student_fatigue, 2),
        room_utilization=round(room_utilization, 2),
        clash_risk=round(clash_risk, 2),
        overall_quality=overall_quality,
    )


def build_suggestions(tenant_id: str, timetable: list[TimetableEntry], conflicts_count: int) -> SuggestionResponse:
    suggestions: list[SuggestionRecord] = []

    if conflicts_count > 0:
        suggestions.append(
            SuggestionRecord(
                suggestion_id="SUG-001",
                suggestion_type="SWAP",
                description="Swap clashing slots to eliminate faculty/room overlaps.",
                expected_quality_delta=8.5,
            )
        )

    faculty_load = Counter(entry.faculty_id for entry in timetable)
    if faculty_load and max(faculty_load.values()) - min(faculty_load.values()) >= 2:
        suggestions.append(
            SuggestionRecord(
                suggestion_id="SUG-002",
                suggestion_type="LOAD_BALANCE",
                description="Redistribute sessions from overloaded faculty to available faculty.",
                expected_quality_delta=6.0,
            )
        )

    room_load = Counter(entry.room for entry in timetable)
    if room_load and len(room_load) > 1:
        suggestions.append(
            SuggestionRecord(
                suggestion_id="SUG-003",
                suggestion_type="IDLE_ROOM",
                description="Move sessions to under-utilized rooms to improve utilization balance.",
                expected_quality_delta=4.0,
            )
        )

    if not suggestions:
        suggestions.append(
            SuggestionRecord(
                suggestion_id="SUG-000",
                suggestion_type="IDLE_ROOM",
                description="Timetable is stable; no major optimization needed.",
                expected_quality_delta=0.5,
            )
        )

    return SuggestionResponse(tenant_id=tenant_id, suggestions=suggestions)


def run_simulation(sim: SimulationRequest) -> SimulationResponse:
    impact_map = {
        "ADD_SECTION": ("New section increases slot pressure; add one room and two faculty blocks.", 2, 74.0),
        "FACULTY_LEAVE": ("Substitution needed for absent faculty; moderate disruption expected.", 1, 78.0),
        "HOLIDAY": ("Compressing week increases fatigue; consider Saturday compensation slots.", 3, 70.0),
        "FIVE_DAY_WEEK": ("Higher daily load concentration; optimize heavy-subject placement.", 2, 72.0),
    }
    summary, conflicts, score = impact_map[sim.scenario_type]
    return SimulationResponse(
        tenant_id=sim.tenant_id,
        scenario_name=sim.scenario_name,
        impact_summary=summary,
        estimated_conflicts=conflicts,
        estimated_quality_score=score,
    )


def emergency_reschedule(payload: EmergencyRescheduleRequest, faculty_pool: list[str]) -> EmergencyRescheduleResponse:
    substitute = next((f for f in faculty_pool if f != payload.affected_faculty_id), payload.affected_faculty_id)
    return EmergencyRescheduleResponse(
        tenant_id=payload.tenant_id,
        handled=True,
        substitute_faculty_id=substitute,
        recommendation=(
            f"Assign substitute faculty {substitute} for section {payload.section}; "
            "shift one low-priority class to nearest free slot to minimize disruption."
        ),
    )


def validate_constraints(rules: list[ConstraintRule]) -> list[str]:
    errors: list[str] = []
    seen = set()
    for rule in rules:
        key = (rule.tenant_id, rule.name)
        if key in seen:
            errors.append(f"Duplicate rule name detected for tenant: {rule.name}")
        seen.add(key)
        if rule.category == "HARD" and rule.weight < 50:
            errors.append(f"Hard rule '{rule.name}' must have weight >= 50")
    return errors
