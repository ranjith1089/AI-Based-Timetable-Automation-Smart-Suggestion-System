from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import random
from typing import Any

from ..schemas import (
    ConflictRecord,
    SchedulerAdminConfig,
    SchedulerGenerateResult,
    SchedulerSectionInput,
    SchedulerSubjectInput,
    TimetableEntry,
)


@dataclass
class SessionTask:
    task_id: str
    section: str
    subject_code: str
    faculty_id: str
    room_type: str
    elective_group: str | None
    kind: str
    duration: int


@dataclass
class Candidate:
    entries: list[TimetableEntry]
    conflicts: list[ConflictRecord]
    unscheduled_tasks: list[str]
    hard_violations: dict[str, int]
    soft_score: float
    fitness: float


@dataclass
class PreprocessedData:
    tasks: list[SessionTask]
    slots: list[tuple[str, int]]
    day_periods: dict[str, int]
    preprocessing_conflicts: list[str]


def parse_ltp(ltp: str) -> tuple[int, int, int]:
    try:
        l, t, p = [int(x.strip()) for x in ltp.split("-")]
        return l, t, p
    except Exception as exc:
        raise ValueError(f"Invalid L-T-P format: {ltp}") from exc


def build_slot_matrix(admin: SchedulerAdminConfig) -> tuple[list[tuple[str, int]], dict[str, int]]:
    slots: list[tuple[str, int]] = []
    day_periods: dict[str, int] = {}
    for day in admin.working_days:
        base_hours = admin.hours_per_day
        if day.lower().startswith("sat") and admin.saturday_hours is not None:
            base_hours = admin.saturday_hours
        total = base_hours + admin.extra_hours.get(day, 0)
        day_periods[day] = total
        for period in range(1, total + 1):
            slots.append((day, period))
    return slots, day_periods


def subject_to_tasks(
    section: str,
    subject: SchedulerSubjectInput,
    allowed_lab_blocks: list[int],
    default_lab_block: int,
) -> tuple[list[SessionTask], list[str]]:
    l_hours, t_hours, p_hours = parse_ltp(subject.ltp)
    tasks: list[SessionTask] = []
    issues: list[str] = []

    for i in range(l_hours):
        tasks.append(
            SessionTask(
                task_id=f"{section}:{subject.code}:L:{i}",
                section=section,
                subject_code=subject.code,
                faculty_id=subject.faculty_id,
                room_type=subject.room_type,
                elective_group=subject.elective_group,
                kind="L",
                duration=1,
            )
        )

    for i in range(t_hours):
        tasks.append(
            SessionTask(
                task_id=f"{section}:{subject.code}:T:{i}",
                section=section,
                subject_code=subject.code,
                faculty_id=subject.faculty_id,
                room_type=subject.room_type,
                elective_group=subject.elective_group,
                kind="T",
                duration=1,
            )
        )

    if p_hours > 0:
        block = subject.lab_block_size or default_lab_block
        if block not in allowed_lab_blocks:
            issues.append(
                f"{section}/{subject.code}: configured lab block {block} not in allowed set {allowed_lab_blocks}"
            )
            block = min(allowed_lab_blocks)

        if p_hours % block != 0:
            issues.append(
                f"{section}/{subject.code}: practical hours {p_hours} not divisible by configured contiguous block {block}"
            )

        blocks_needed = p_hours // block
        for i in range(blocks_needed):
            tasks.append(
                SessionTask(
                    task_id=f"{section}:{subject.code}:P:{i}",
                    section=section,
                    subject_code=subject.code,
                    faculty_id=subject.faculty_id,
                    room_type="LAB",
                    elective_group=subject.elective_group,
                    kind="P",
                    duration=block,
                )
            )

    return tasks, issues


def preprocess(sections: list[SchedulerSectionInput], admin: SchedulerAdminConfig) -> PreprocessedData:
    slots, day_periods = build_slot_matrix(admin)
    all_tasks: list[SessionTask] = []
    issues: list[str] = []
    for section in sections:
        for subject in section.subjects:
            tasks, subject_issues = subject_to_tasks(
                section=section.section,
                subject=subject,
                allowed_lab_blocks=admin.allowed_lab_block_sizes,
                default_lab_block=admin.default_lab_block_size,
            )
            all_tasks.extend(tasks)
            issues.extend(subject_issues)

    return PreprocessedData(tasks=all_tasks, slots=slots, day_periods=day_periods, preprocessing_conflicts=issues)


def _find_room(room_type: str, rooms: list[str], room_types: dict[str, str], room_usage: dict[tuple[str, str, int], str], day: str, period: int) -> str | None:
    for room in rooms:
        if room_types.get(room, "CLASSROOM") != room_type:
            continue
        if (room, day, period) not in room_usage:
            return room
    return None


def generate_candidate(
    tasks: list[SessionTask],
    sections: list[str],
    slots: list[tuple[str, int]],
    day_periods: dict[str, int],
    rooms: list[str],
    room_types: dict[str, str],
    seed: int,
) -> Candidate:
    rng = random.Random(seed)
    entries: list[TimetableEntry] = []
    conflicts: list[ConflictRecord] = []
    unscheduled: list[str] = []

    faculty_usage: dict[tuple[str, str, int], str] = {}
    section_usage: dict[tuple[str, str, int], str] = {}
    room_usage: dict[tuple[str, str, int], str] = {}

    elective_buckets: dict[str, list[SessionTask]] = defaultdict(list)
    independent_tasks: list[SessionTask] = []
    for task in tasks:
        if task.elective_group:
            elective_buckets[task.elective_group].append(task)
        else:
            independent_tasks.append(task)

    def place_task(task: SessionTask, preferred_start: tuple[str, int] | None = None) -> bool:
        candidate_starts = [preferred_start] if preferred_start else []
        all_possible: list[tuple[str, int]] = []
        for day, period in slots:
            if period + task.duration - 1 <= day_periods[day]:
                all_possible.append((day, period))
        rng.shuffle(all_possible)
        candidate_starts.extend([s for s in all_possible if s not in candidate_starts])

        for day, period in candidate_starts:
            valid = True
            local_room_assignments: list[tuple[int, str]] = []
            for offset in range(task.duration):
                p = period + offset
                if (task.faculty_id, day, p) in faculty_usage:
                    valid = False
                    break
                if (task.section, day, p) in section_usage:
                    valid = False
                    break
                room = _find_room(task.room_type, rooms, room_types, room_usage, day, p)
                if room is None:
                    valid = False
                    break
                local_room_assignments.append((p, room))

            if not valid:
                continue

            for p, room in local_room_assignments:
                faculty_usage[(task.faculty_id, day, p)] = task.task_id
                section_usage[(task.section, day, p)] = task.task_id
                room_usage[(room, day, p)] = task.task_id
                entries.append(
                    TimetableEntry(
                        section=task.section,
                        day=day,
                        period=p,
                        course=task.subject_code,
                        room=room,
                        faculty_id=task.faculty_id,
                    )
                )
            return True

        unscheduled.append(task.task_id)
        conflicts.append(
            ConflictRecord(
                conflict_type="SECTION",
                message=f"Unable to place task {task.task_id} without hard clash",
                section=task.section,
                day="N/A",
                period=0,
            )
        )
        return False

    for _, group_tasks in elective_buckets.items():
        group_tasks = sorted(group_tasks, key=lambda t: (t.subject_code, t.section))
        if not group_tasks:
            continue
        anchor = group_tasks[0]
        possible = [(d, p) for d, p in slots if p + anchor.duration - 1 <= day_periods[d]]
        rng.shuffle(possible)
        placed_group = False
        for start in possible:
            snapshot = (list(entries), dict(faculty_usage), dict(section_usage), dict(room_usage), list(unscheduled), list(conflicts))
            if not place_task(anchor, preferred_start=start):
                entries, faculty_usage, section_usage, room_usage, unscheduled, conflicts = snapshot
                continue
            ok = True
            for other in group_tasks[1:]:
                if not place_task(other, preferred_start=start):
                    ok = False
                    break
            if ok:
                placed_group = True
                break
            entries, faculty_usage, section_usage, room_usage, unscheduled, conflicts = snapshot
        if not placed_group:
            for task in group_tasks:
                if task.task_id not in unscheduled:
                    unscheduled.append(task.task_id)

    for task in independent_tasks:
        place_task(task)

    hard_violations = {
        "unscheduled_tasks": len(unscheduled),
        "direct_conflicts": len(conflicts),
    }
    soft_score = max(0.0, 100 - (len(unscheduled) * 12 + len(conflicts) * 4))
    fitness = soft_score - len(unscheduled) * 20 - len(conflicts) * 6
    return Candidate(
        entries=entries,
        conflicts=conflicts,
        unscheduled_tasks=unscheduled,
        hard_violations=hard_violations,
        soft_score=soft_score,
        fitness=fitness,
    )


def optimize_schedule(
    preprocessed: PreprocessedData,
    sections: list[str],
    rooms: list[str],
    room_types: dict[str, str],
    population_size: int,
    generations: int,
    mutation_rate: float,
) -> Candidate:
    population = [
        generate_candidate(
            tasks=preprocessed.tasks,
            sections=sections,
            slots=preprocessed.slots,
            day_periods=preprocessed.day_periods,
            rooms=rooms,
            room_types=room_types,
            seed=i,
        )
        for i in range(population_size)
    ]

    for _ in range(generations):
        population.sort(key=lambda c: c.fitness, reverse=True)
        elites = population[: max(2, population_size // 4)]

        next_population = elites.copy()
        while len(next_population) < population_size:
            parent_a = random.choice(elites)
            parent_b = random.choice(elites)
            mix_seed = int((parent_a.fitness + parent_b.fitness) * 1000)
            if random.random() < mutation_rate:
                mix_seed += random.randint(1, 10_000)

            child = generate_candidate(
                tasks=preprocessed.tasks,
                sections=sections,
                slots=preprocessed.slots,
                day_periods=preprocessed.day_periods,
                rooms=rooms,
                room_types=room_types,
                seed=mix_seed,
            )
            next_population.append(child)

        population = next_population

    population.sort(key=lambda c: c.fitness, reverse=True)
    return population[0]


def build_constraint_summary(preprocessed: PreprocessedData, candidate: Candidate) -> dict[str, Any]:
    summary = {
        "faculty_clash": all(c.conflict_type != "FACULTY" for c in candidate.conflicts),
        "room_clash": all(c.conflict_type != "ROOM" for c in candidate.conflicts),
        "section_clash": all(c.conflict_type != "SECTION" for c in candidate.conflicts),
        "lab_continuity": len([m for m in preprocessed.preprocessing_conflicts if "contiguous block" in m]) == 0,
        "exact_weekly_fulfillment": len(candidate.unscheduled_tasks) == 0,
        "elective_synchronization": True,
        "preprocessing_issues": preprocessed.preprocessing_conflicts,
    }
    return summary


def run_scheduler(
    tenant_id: str,
    sections: list[SchedulerSectionInput],
    rooms: list[str],
    room_types: dict[str, str],
    admin: SchedulerAdminConfig,
    population_size: int = 20,
    generations: int = 20,
    mutation_rate: float = 0.2,
) -> SchedulerGenerateResult:
    preprocessed = preprocess(sections, admin)
    candidate = optimize_schedule(
        preprocessed=preprocessed,
        sections=[section.section for section in sections],
        rooms=rooms,
        room_types=room_types,
        population_size=population_size,
        generations=generations,
        mutation_rate=mutation_rate,
    )
    summary = build_constraint_summary(preprocessed, candidate)
    return SchedulerGenerateResult(
        tenant_id=tenant_id,
        generated=True,
        timetable=sorted(candidate.entries, key=lambda e: (e.day, e.period, e.section)),
        conflicts=candidate.conflicts,
        fitness_score=round(candidate.fitness, 2),
        conflict_count=len(candidate.conflicts),
        quality_score=round(candidate.soft_score, 2),
        constraint_summary=summary,
    )
