from collections import Counter, defaultdict
from statistics import mean

from .schemas import (
    ConflictRecord,
    ConstraintRule,
    ElectiveGroup,
    EmergencyRescheduleRequest,
    EmergencyRescheduleResponse,
    QualityResponse,
    SectionSubjectPlan,
    SimulationRequest,
    SimulationResponse,
    SuggestionRecord,
    SuggestionResponse,
    TimetableEntry,
)

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
MAX_PERIODS_PER_DAY = 7


def _expand_section_subject_blocks(section_plans: list[SectionSubjectPlan]) -> dict[str, list[dict[str, str | bool]]]:
    plan_map: dict[str, list[dict[str, str | bool]]] = {}
    for section_plan in section_plans:
        blocks: list[dict[str, str | bool]] = []
        for block in section_plan.subject_blocks:
            for _ in range(block.required_periods):
                blocks.append({"course": block.subject, "is_lab": block.is_lab})
        plan_map[section_plan.section] = blocks
    return plan_map


def _pair_with_bipartite_matching(
    sessions: list[dict],
    faculty_ids: list[str],
    rooms: list[str],
) -> bool:
    """Assign each pending session a faculty and room using bipartite matching."""

    if len(faculty_ids) < len(sessions):
        return False

    faculty_edges = {idx: list(faculty_ids) for idx in range(len(sessions))}
    faculty_to_session: dict[str, int] = {}

    def _dfs_faculty(session_idx: int, visited: set[str]) -> bool:
        for faculty in faculty_edges[session_idx]:
            if faculty in visited:
                continue
            visited.add(faculty)
            if faculty not in faculty_to_session or _dfs_faculty(faculty_to_session[faculty], visited):
                faculty_to_session[faculty] = session_idx
                return True
        return False

    if sum(1 for idx in range(len(sessions)) if _dfs_faculty(idx, set())) != len(sessions):
        return False

    for faculty, session_idx in faculty_to_session.items():
        sessions[session_idx]["faculty_id"] = faculty

    room_edges: dict[int, list[str]] = {}
    for idx, session in enumerate(sessions):
        allowed = [room for room in rooms if ("LAB" in room.upper()) == bool(session["is_lab"])]
        if len(allowed) < len(sessions):
            allowed = list(rooms)
        room_edges[idx] = allowed or list(rooms)

    room_to_session: dict[str, int] = {}

    def _dfs_room(session_idx: int, visited: set[str]) -> bool:
        for room in room_edges[session_idx]:
            if room in visited:
                continue
            visited.add(room)
            if room not in room_to_session or _dfs_room(room_to_session[room], visited):
                room_to_session[room] = session_idx
                return True
        return False

    if sum(1 for idx in range(len(sessions)) if _dfs_room(idx, set())) != len(sessions):
        return False

    for room, session_idx in room_to_session.items():
        sessions[session_idx]["room"] = room

    return True


def generate_section_aware_timetable(
    tenant_id: str,
    sections: list[str],
    courses: list[str],
    rooms: list[str],
    faculty_ids: list[str],
    section_subject_plan: list[SectionSubjectPlan],
    elective_groups: list[ElectiveGroup],
) -> list[TimetableEntry]:
    section_blocks = _expand_section_subject_blocks(section_subject_plan)
    if not section_blocks:
        section_blocks = {section: [{"course": courses[idx % len(courses)], "is_lab": False}] for idx, section in enumerate(sections)}

    for section in sections:
        section_blocks.setdefault(section, [{"course": courses[0], "is_lab": False}])

    entries: list[TimetableEntry] = []
    used_by_section: set[tuple[str, str, int]] = set()
    used_by_faculty: set[tuple[str, str, int]] = set()
    used_by_room: set[tuple[str, str, int]] = set()

    # Hard constraint: elective groups must be synchronized across sections.
    for elective_idx, group in enumerate(elective_groups):
        day = DAYS[elective_idx % len(DAYS)]
        period = (elective_idx % MAX_PERIODS_PER_DAY) + 1
        elective_sessions = [
            {
                "section": section,
                "course": group.subject,
                "is_lab": False,
            }
            for section in group.sections
        ]

        if not _pair_with_bipartite_matching(elective_sessions, group.faculty_ids, group.room_ids):
            raise ValueError(f"Unable to assign faculty-room pairs for elective group '{group.group_id}'")

        for session in elective_sessions:
            faculty_key = (session["faculty_id"], day, period)
            room_key = (session["room"], day, period)
            section_key = (session["section"], day, period)
            if faculty_key in used_by_faculty:
                raise ValueError("Cross-section faculty overlap detected while scheduling elective groups")
            if room_key in used_by_room or section_key in used_by_section:
                raise ValueError("Unable to enforce synchronized elective slots without overlap")

            used_by_faculty.add(faculty_key)
            used_by_room.add(room_key)
            used_by_section.add(section_key)
            entries.append(
                TimetableEntry(
                    section=session["section"],
                    day=day,
                    period=period,
                    course=group.subject,
                    room=session["room"],
                    faculty_id=session["faculty_id"],
                )
            )

        for section in group.sections:
            section_blocks[section] = [block for block in section_blocks[section] if block["course"] != group.subject]

    # Remaining section-specific sessions.
    cursors = {section: 0 for section in section_blocks}
    pending_sections = [section for section, blocks in section_blocks.items() if blocks]
    slot_idx = 0

    while pending_sections:
        day = DAYS[(slot_idx // MAX_PERIODS_PER_DAY) % len(DAYS)]
        period = (slot_idx % MAX_PERIODS_PER_DAY) + 1
        candidate_sessions: list[dict] = []

        for section in list(pending_sections):
            block_idx = cursors[section]
            if block_idx >= len(section_blocks[section]):
                pending_sections.remove(section)
                continue
            if (section, day, period) in used_by_section:
                continue
            block = section_blocks[section][block_idx]
            candidate_sessions.append({"section": section, "course": block["course"], "is_lab": block["is_lab"]})

        if candidate_sessions and _pair_with_bipartite_matching(candidate_sessions, faculty_ids, rooms):
            for session in candidate_sessions:
                faculty_key = (session["faculty_id"], day, period)
                room_key = (session["room"], day, period)
                section_key = (session["section"], day, period)
                if faculty_key in used_by_faculty or room_key in used_by_room or section_key in used_by_section:
                    continue

                used_by_faculty.add(faculty_key)
                used_by_room.add(room_key)
                used_by_section.add(section_key)
                entries.append(
                    TimetableEntry(
                        section=session["section"],
                        day=day,
                        period=period,
                        course=str(session["course"]),
                        room=str(session["room"]),
                        faculty_id=str(session["faculty_id"]),
                    )
                )
                cursors[session["section"]] += 1

        pending_sections = [section for section in pending_sections if cursors[section] < len(section_blocks[section])]
        slot_idx += 1
        if slot_idx > len(DAYS) * MAX_PERIODS_PER_DAY * 4:
            raise ValueError("Unable to place all section subject blocks within available slots")

    return entries


def detect_conflicts(timetable: list[TimetableEntry], elective_groups: list[ElectiveGroup] | None = None) -> list[ConflictRecord]:
    conflicts: list[ConflictRecord] = []
    faculty_map: dict[tuple[str, str, int], list[TimetableEntry]] = defaultdict(list)
    room_map: dict[tuple[str, str, int], list[TimetableEntry]] = defaultdict(list)
    section_map: dict[tuple[str, str, int], list[TimetableEntry]] = defaultdict(list)

    for entry in timetable:
        faculty_map[(entry.faculty_id, entry.day, entry.period)].append(entry)
        room_map[(entry.room, entry.day, entry.period)].append(entry)
        section_map[(entry.section, entry.day, entry.period)].append(entry)

    for (_, day, period), entries in faculty_map.items():
        if len(entries) > 1:
            for entry in entries:
                conflicts.append(
                    ConflictRecord(
                        conflict_type="FACULTY",
                        message=f"Cross-section faculty overlap for {entry.faculty_id} at same slot",
                        section=entry.section,
                        day=day,
                        period=period,
                    )
                )

    for (_, day, period), entries in room_map.items():
        if len(entries) > 1:
            for entry in entries:
                conflicts.append(
                    ConflictRecord(
                        conflict_type="ROOM",
                        message=f"Room {entry.room} double-booked at period {period}",
                        section=entry.section,
                        day=day,
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

    if elective_groups:
        for group in elective_groups:
            group_entries = [entry for entry in timetable if entry.section in group.sections and entry.course == group.subject]
            grouped_slots = {(entry.day, entry.period) for entry in group_entries}
            if len(grouped_slots) != 1 or len(group_entries) != len(group.sections):
                first = group_entries[0] if group_entries else None
                conflicts.append(
                    ConflictRecord(
                        conflict_type="SECTION",
                        message=f"Elective group {group.group_id} is not synchronized across sections",
                        section=first.section if first else group.sections[0],
                        day=first.day if first else DAYS[0],
                        period=first.period if first else 1,
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
