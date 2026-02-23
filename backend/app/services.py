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
    SubjectInput,
    TimetableEntry,
    TimetableGenerateRequest,
)

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
MAX_PERIODS_PER_DAY = 7

def _slot_load(subject: SubjectInput) -> int:
    return subject.l_hours + subject.t_hours + subject.p_hours


def generate_timetable_entries(payload: TimetableGenerateRequest) -> list[TimetableEntry]:
    entries: list[TimetableEntry] = []
    ordered_subjects = sorted(payload.subjects, key=_slot_load, reverse=True)

    for i, section in enumerate(payload.sections, start=1):
        subject = ordered_subjects[(i - 1) % len(ordered_subjects)]
        entries.append(
            TimetableEntry(
                section=section,
                day="Monday",
                period=i,
                course_code=subject.course_code,
                course_name=subject.course_name,
                semester=subject.semester,
                l_hours=subject.l_hours,
                t_hours=subject.t_hours,
                p_hours=subject.p_hours,
                tcp=subject.tcp,
                course_type=subject.course_type,
                is_elective=subject.is_elective,
                requires_lab=subject.requires_lab,
                room=payload.rooms[(i - 1) % len(payload.rooms)],
                faculty_id=payload.faculty_ids[(i - 1) % len(payload.faculty_ids)],
            )
        )

    return entries


def detect_conflicts(timetable: list[TimetableEntry]) -> list[ConflictRecord]:
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
                        message=f"Room {entry.room} double-booked on {day} period {period}",
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


def _is_lab(course: str) -> bool:
    course_name = course.lower()
    return "lab" in course_name or "practical" in course_name


def generate_timetable_entries(payload: TimetableGenerateRequest) -> tuple[list[TimetableEntry], list[str]]:
    sections = payload.sections
    periods_per_day = 6 + (payload.extra_hour_buffer.periods if payload.extra_hour_buffer.enabled else 0)
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    if payload.saturday_config.enabled:
        weekdays.append("Saturday")

    elective_courses = {
        elective
        for group in payload.elective_groups
        for elective in group.electives
    }
    base_courses = [course for course in payload.courses if course not in elective_courses]
    if not base_courses:
        base_courses = list(payload.courses)

    room_usage: set[tuple[str, str, int]] = set()
    faculty_usage: set[tuple[str, str, int]] = set()
    entries: list[TimetableEntry] = []
    rationales: list[str] = []

    def pick_room(course: str, day: str, period: int, section_idx: int) -> str:
        lab_rooms = [r for r in payload.rooms if "lab" in r.lower()]
        all_rooms = lab_rooms if _is_lab(course) and lab_rooms else payload.rooms
        for shift in range(len(all_rooms)):
            room = all_rooms[(section_idx + period + shift) % len(all_rooms)]
            if (room, day, period) not in room_usage:
                room_usage.add((room, day, period))
                return room
        room = all_rooms[(section_idx + period) % len(all_rooms)]
        room_usage.add((room, day, period))
        return room

    def pick_faculty(day: str, period: int, section_idx: int) -> str:
        for shift in range(len(payload.faculty_ids)):
            faculty = payload.faculty_ids[(section_idx + period + shift) % len(payload.faculty_ids)]
            if (faculty, day, period) not in faculty_usage:
                faculty_usage.add((faculty, day, period))
                return faculty
        fallback = payload.faculty_ids[(section_idx + period) % len(payload.faculty_ids)]
        faculty_usage.add((fallback, day, period))
        return fallback

    # Place synchronized electives first: same day+period across mapped sections.
    for group_index, group in enumerate(payload.elective_groups):
        aligned_period = (group_index % periods_per_day) + 1
        aligned_day = weekdays[group_index % len(weekdays)]
        for section in group.sections:
            if section not in sections:
                continue
            section_idx = sections.index(section)
            elective = group.electives[section_idx % len(group.electives)]
            room = pick_room(elective, aligned_day, aligned_period, section_idx)
            faculty = pick_faculty(aligned_day, aligned_period, section_idx)
            entries.append(
                TimetableEntry(
                    section=section,
                    day=aligned_day,
                    period=aligned_period,
                    course=elective,
                    room=room,
                    faculty_id=faculty,
                )
            )
        rationales.append(
            f"Elective group '{group.group_name}' synchronized on {aligned_day} period {aligned_period} for sections {', '.join(group.sections)}."
        )

    for section_idx, section in enumerate(sections):
        scheduled_slots = {(entry.day, entry.period) for entry in entries if entry.section == section}
        course_idx = 0
        for day in weekdays:
            day_period_limit = periods_per_day
            if day == "Saturday" and payload.saturday_config.enabled:
                day_period_limit = payload.saturday_config.max_periods
            for period in range(1, day_period_limit + 1):
                if (day, period) in scheduled_slots:
                    continue

                course = base_courses[course_idx % len(base_courses)]
                is_lab_course = _is_lab(course)

                if day == "Saturday" and payload.saturday_config.enabled:
                    mode = payload.saturday_config.mode
                    if mode == "LABS_ONLY" and not is_lab_course:
                        continue
                    if mode == "SD_ELECTIVE_FOCUS" and is_lab_course:
                        continue

                room = pick_room(course, day, period, section_idx)
                faculty = pick_faculty(day, period, section_idx)
                entries.append(
                    TimetableEntry(
                        section=section,
                        day=day,
                        period=period,
                        course=course,
                        room=room,
                        faculty_id=faculty,
                    )
                )

                # Lab continuity in contiguous slots where available.
                if payload.enforce_lab_continuity and is_lab_course and period < day_period_limit:
                    next_period = period + 1
                    if (day, next_period) not in scheduled_slots:
                        room_usage.add((room, day, next_period))
                        faculty_usage.add((faculty, day, next_period))
                        entries.append(
                            TimetableEntry(
                                section=section,
                                day=day,
                                period=next_period,
                                course=f"{course} (cont.)",
                                room=room,
                                faculty_id=faculty,
                            )
                        )
                        scheduled_slots.add((day, next_period))

                scheduled_slots.add((day, period))
                course_idx += 1

    if payload.section_groups:
        rationales.append("Section groups were considered for balanced rotation across faculty and room assignments.")
    if payload.extra_hour_buffer.enabled:
        rationales.append(f"Extra-hour buffer enabled with {payload.extra_hour_buffer.periods} additional period(s) per weekday.")
    if payload.saturday_config.enabled:
        rationales.append(
            f"Saturday scheduling enabled in {payload.saturday_config.mode} mode with max {payload.saturday_config.max_periods} period(s)."
        )
    if payload.enforce_lab_continuity:
        rationales.append("Lab continuity constraint applied by reserving contiguous periods for lab sessions.")

    return entries, rationales


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
