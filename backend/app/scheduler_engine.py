from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Literal

from .schemas import (
    AdminConfig,
    AssignmentConflict,
    RoomSpec,
    SchedulerDiagnostics,
    ScoreBreakdown,
    SubjectSpec,
    TimetableEntry,
)

DayName = str


@dataclass(frozen=True)
class PeriodBlock:
    section: str
    subject: str
    faculty_id: str
    kind: Literal["LECTURE", "TUTORIAL", "LAB"]
    length: int
    block_id: str
    difficulty: int


class SchedulerEngine:
    def __init__(self, seed: int = 42) -> None:
        self.rng = Random(seed)

    def generate(
        self,
        sections: list[str],
        subjects: list[SubjectSpec],
        rooms: list[RoomSpec],
        config: AdminConfig,
        ga_config: dict[str, int] | None = None,
    ) -> tuple[list[TimetableEntry], ScoreBreakdown, SchedulerDiagnostics]:
        blocks = self._expand_subject_blocks(sections, subjects)
        slots = self._build_slot_matrix(config)

        population_size = (ga_config or {}).get("population_size", 20)
        generations = (ga_config or {}).get("generations", 30)
        mutation_rate = (ga_config or {}).get("mutation_rate", 20)

        block_map = {block.block_id: block for block in blocks}
        population = [self._construct_candidate(blocks, slots, rooms, block_map) for _ in range(population_size)]
        population = [self._repair_candidate(candidate, slots, rooms, block_map) for candidate in population]

        best_candidate = population[0]
        best_fitness, best_breakdown, best_diags = self._fitness(best_candidate, blocks, slots)

        for _ in range(generations):
            scored = []
            for candidate in population:
                fitness, breakdown, diagnostics = self._fitness(candidate, blocks, slots)
                scored.append((fitness, candidate, breakdown, diagnostics))

            scored.sort(key=lambda item: item[0], reverse=True)
            if scored[0][0] > best_fitness:
                best_fitness, best_candidate, best_breakdown, best_diags = scored[0]

            parents = [item[1] for item in scored[: max(2, population_size // 2)]]
            next_generation: list[dict[str, tuple[DayName, int, str]]] = [scored[0][1]]

            while len(next_generation) < population_size:
                p1 = self.rng.choice(parents)
                p2 = self.rng.choice(parents)
                child = self._crossover(p1, p2)
                child = self._mutate(child, slots, rooms, mutation_rate)
                child = self._repair_candidate(child, slots, rooms, block_map)
                next_generation.append(child)

            population = next_generation

        timetable_entries = self._to_timetable_entries(best_candidate, block_map)
        return timetable_entries, best_breakdown, best_diags

    def _expand_subject_blocks(self, sections: list[str], subjects: list[SubjectSpec]) -> list[PeriodBlock]:
        blocks: list[PeriodBlock] = []
        for section in sections:
            for subject in subjects:
                lecture, tutorial, practical = subject.ltp
                serial = 1
                for _ in range(lecture):
                    blocks.append(
                        PeriodBlock(
                            section=section,
                            subject=subject.subject,
                            faculty_id=subject.faculty_id,
                            kind="LECTURE",
                            length=1,
                            block_id=f"{section}-{subject.subject}-L{serial}",
                            difficulty=subject.difficulty,
                        )
                    )
                    serial += 1
                for _ in range(tutorial):
                    blocks.append(
                        PeriodBlock(
                            section=section,
                            subject=subject.subject,
                            faculty_id=subject.faculty_id,
                            kind="TUTORIAL",
                            length=1,
                            block_id=f"{section}-{subject.subject}-T{serial}",
                            difficulty=subject.difficulty,
                        )
                    )
                    serial += 1

                if practical > 0:
                    lab_block_size = subject.lab_block_size or practical
                    full_blocks = practical // lab_block_size
                    remainder = practical % lab_block_size
                    for b in range(full_blocks):
                        blocks.append(
                            PeriodBlock(
                                section=section,
                                subject=subject.subject,
                                faculty_id=subject.faculty_id,
                                kind="LAB",
                                length=lab_block_size,
                                block_id=f"{section}-{subject.subject}-P{b + 1}",
                                difficulty=subject.difficulty,
                            )
                        )
                    if remainder:
                        blocks.append(
                            PeriodBlock(
                                section=section,
                                subject=subject.subject,
                                faculty_id=subject.faculty_id,
                                kind="LAB",
                                length=remainder,
                                block_id=f"{section}-{subject.subject}-P{full_blocks + 1}",
                                difficulty=subject.difficulty,
                            )
                        )
        return blocks

    def _build_slot_matrix(self, config: AdminConfig) -> list[tuple[DayName, int]]:
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        if config.include_saturday:
            days.append("Saturday")
        if config.days:
            days = config.days

        slots: list[tuple[DayName, int]] = []
        for day in days:
            for period in range(1, config.hours_per_day + config.extra_slots + 1):
                slots.append((day, period))
        return slots

    def _construct_candidate(
        self,
        blocks: list[PeriodBlock],
        slots: list[tuple[DayName, int]],
        rooms: list[RoomSpec],
        block_map: dict[str, PeriodBlock],
    ) -> dict[str, tuple[DayName, int, str]]:
        assignments: dict[str, tuple[DayName, int, str]] = {}
        for block in blocks:
            candidate_slots = slots[:]
            self.rng.shuffle(candidate_slots)
            chosen = None
            for day, period in candidate_slots:
                room_pool = self._compatible_rooms(block, rooms)
                if not room_pool:
                    continue
                room = self.rng.choice(room_pool)
                if self._can_place(assignments, block, day, period, room, slots, block_map):
                    chosen = (day, period, room)
                    break
            if chosen is None:
                room = self.rng.choice(self._compatible_rooms(block, rooms) or [rooms[0].name])
                day, period = self.rng.choice(slots)
                chosen = (day, period, room)
            assignments[block.block_id] = chosen
        return assignments

    def _can_place(
        self,
        assignments: dict[str, tuple[DayName, int, str]],
        block: PeriodBlock,
        day: DayName,
        period: int,
        room: str,
        slots: list[tuple[DayName, int]],
        block_map: dict[str, PeriodBlock],
    ) -> bool:
        for offset in range(block.length):
            if (day, period + offset) not in slots:
                return False

        for assigned_id, (a_day, a_period, a_room) in assignments.items():
            assigned_block = block_map[assigned_id]
            for offset in range(block.length):
                target_period = period + offset
                for a_offset in range(assigned_block.length):
                    occupied_period = a_period + a_offset
                    if a_day == day and occupied_period == target_period:
                        if assigned_block.faculty_id == block.faculty_id:
                            return False
                        if assigned_block.section == block.section:
                            return False
                        if a_room == room:
                            return False

        return True

    def _repair_candidate(
        self,
        candidate: dict[str, tuple[DayName, int, str]],
        slots: list[tuple[DayName, int]],
        rooms: list[RoomSpec],
        block_map: dict[str, PeriodBlock],
    ) -> dict[str, tuple[DayName, int, str]]:
        # Light CSP-repair: reassign items that violate hard constraints.
        fixed = dict(candidate)
        occupied_faculty: set[tuple[str, DayName, int]] = set()
        occupied_room: set[tuple[str, DayName, int]] = set()
        occupied_section: set[tuple[str, DayName, int]] = set()

        for block_id in list(fixed.keys()):
            day, period, room = fixed[block_id]
            block = block_map[block_id]

            def has_conflict(test_day: DayName, test_period: int, test_room: str) -> bool:
                if block.kind == "LAB" and test_room not in self._compatible_rooms(block, rooms):
                    return True
                for offset in range(block.length):
                    slot = (test_day, test_period + offset)
                    if slot not in slots:
                        return True
                    if (block.faculty_id, test_day, test_period + offset) in occupied_faculty:
                        return True
                    if (test_room, test_day, test_period + offset) in occupied_room:
                        return True
                    if (block.section, test_day, test_period + offset) in occupied_section:
                        return True
                return False

            if has_conflict(day, period, room):
                reassigned = False
                for alt_day, alt_period in slots:
                    for alt_room in self._compatible_rooms(block, rooms):
                        if has_conflict(alt_day, alt_period, alt_room):
                            continue
                        fixed[block_id] = (alt_day, alt_period, alt_room)
                        day, period, room = alt_day, alt_period, alt_room
                        reassigned = True
                        break
                    if reassigned:
                        break
                if not reassigned:
                    compatible = self._compatible_rooms(block, rooms)
                    fallback_room = compatible[0] if compatible else rooms[0].name
                    fixed[block_id] = (slots[0][0], slots[0][1], fallback_room)
                    day, period, room = fixed[block_id]

            for offset in range(block.length):
                occupied_faculty.add((block.faculty_id, day, period + offset))
                occupied_room.add((room, day, period + offset))
                occupied_section.add((block.section, day, period + offset))

        return fixed

    def _crossover(
        self,
        left: dict[str, tuple[DayName, int, str]],
        right: dict[str, tuple[DayName, int, str]],
    ) -> dict[str, tuple[DayName, int, str]]:
        child: dict[str, tuple[DayName, int, str]] = {}
        keys = list(left.keys())
        split = self.rng.randint(0, len(keys) - 1) if keys else 0
        left_keys = set(keys[:split])
        for key in keys:
            child[key] = left[key] if key in left_keys else right.get(key, left[key])
        return child

    def _mutate(
        self,
        candidate: dict[str, tuple[DayName, int, str]],
        slots: list[tuple[DayName, int]],
        rooms: list[RoomSpec],
        mutation_rate: int,
    ) -> dict[str, tuple[DayName, int, str]]:
        mutated = dict(candidate)
        room_names = [room.name for room in rooms]
        for block_id in mutated:
            if self.rng.randint(1, 100) <= mutation_rate:
                day, period = self.rng.choice(slots)
                room = self.rng.choice(room_names)
                mutated[block_id] = (day, period, room)
        return mutated

    def _fitness(
        self,
        candidate: dict[str, tuple[DayName, int, str]],
        blocks: list[PeriodBlock],
        slots: list[tuple[DayName, int]],
    ) -> tuple[float, ScoreBreakdown, SchedulerDiagnostics]:
        block_map = {block.block_id: block for block in blocks}
        hard_conflicts: list[AssignmentConflict] = []

        faculty_seen: dict[tuple[str, DayName, int], str] = {}
        room_seen: dict[tuple[str, DayName, int], str] = {}
        section_seen: dict[tuple[str, DayName, int], str] = {}

        for block_id, (day, period, room) in candidate.items():
            block = block_map[block_id]
            for offset in range(block.length):
                current_period = period + offset
                if (day, current_period) not in slots:
                    hard_conflicts.append(
                        AssignmentConflict(
                            conflict_type="SECTION",
                            message=f"{block.block_id} exceeds configured matrix window",
                            section=block.section,
                            day=day,
                            period=current_period,
                        )
                    )
                    continue
                f_key = (block.faculty_id, day, current_period)
                r_key = (room, day, current_period)
                s_key = (block.section, day, current_period)

                if f_key in faculty_seen:
                    hard_conflicts.append(
                        AssignmentConflict(
                            conflict_type="FACULTY",
                            message=f"Faculty clash between {faculty_seen[f_key]} and {block.block_id}",
                            section=block.section,
                            day=day,
                            period=current_period,
                        )
                    )
                else:
                    faculty_seen[f_key] = block.block_id

                if r_key in room_seen:
                    hard_conflicts.append(
                        AssignmentConflict(
                            conflict_type="ROOM",
                            message=f"Room clash between {room_seen[r_key]} and {block.block_id}",
                            section=block.section,
                            day=day,
                            period=current_period,
                        )
                    )
                else:
                    room_seen[r_key] = block.block_id

                if s_key in section_seen:
                    hard_conflicts.append(
                        AssignmentConflict(
                            conflict_type="SECTION",
                            message=f"Section clash between {section_seen[s_key]} and {block.block_id}",
                            section=block.section,
                            day=day,
                            period=current_period,
                        )
                    )
                else:
                    section_seen[s_key] = block.block_id

        subject_spread_penalty = self._spread_penalty(candidate, block_map)
        fatigue_penalty = self._fatigue_penalty(candidate, block_map)
        heavy_subject_penalty = self._heavy_subject_penalty(candidate, block_map)

        hard_penalty = len(hard_conflicts) * 100
        soft_penalty = subject_spread_penalty + fatigue_penalty + heavy_subject_penalty
        total_penalty = hard_penalty + soft_penalty
        fitness = max(0.0, 1000.0 - total_penalty)

        breakdown = ScoreBreakdown(
            hard_penalty=hard_penalty,
            subject_spread_penalty=subject_spread_penalty,
            fatigue_penalty=fatigue_penalty,
            heavy_subject_penalty=heavy_subject_penalty,
            final_score=fitness,
        )
        diagnostics = SchedulerDiagnostics(
            hard_conflicts=hard_conflicts,
            soft_constraint_notes=[
                f"Subject spread penalty: {subject_spread_penalty}",
                f"Fatigue penalty: {fatigue_penalty}",
                f"Heavy subject penalty: {heavy_subject_penalty}",
            ],
        )
        return fitness, breakdown, diagnostics

    def _spread_penalty(
        self,
        candidate: dict[str, tuple[DayName, int, str]],
        block_map: dict[str, PeriodBlock],
    ) -> int:
        day_map: dict[tuple[str, str], set[str]] = {}
        for block_id, (day, _, _) in candidate.items():
            block = block_map[block_id]
            key = (block.section, block.subject)
            day_map.setdefault(key, set()).add(day)

        penalty = 0
        for days in day_map.values():
            if len(days) == 1:
                penalty += 15
        return penalty

    def _fatigue_penalty(
        self,
        candidate: dict[str, tuple[DayName, int, str]],
        block_map: dict[str, PeriodBlock],
    ) -> int:
        by_section_day: dict[tuple[str, str], list[int]] = {}
        for block_id, (day, period, _) in candidate.items():
            block = block_map[block_id]
            by_section_day.setdefault((block.section, day), []).append(period)

        penalty = 0
        for periods in by_section_day.values():
            periods.sort()
            streak = 1
            for i in range(1, len(periods)):
                if periods[i] == periods[i - 1] + 1:
                    streak += 1
                else:
                    streak = 1
                if streak > 3:
                    penalty += 8
        return penalty

    def _heavy_subject_penalty(
        self,
        candidate: dict[str, tuple[DayName, int, str]],
        block_map: dict[str, PeriodBlock],
    ) -> int:
        heavy_by_day: dict[tuple[str, str], int] = {}
        for block_id, (day, _, _) in candidate.items():
            block = block_map[block_id]
            if block.difficulty >= 4:
                heavy_by_day[(block.section, day)] = heavy_by_day.get((block.section, day), 0) + 1

        penalty = 0
        for count in heavy_by_day.values():
            if count > 2:
                penalty += (count - 2) * 6
        return penalty

    def _to_timetable_entries(
        self,
        candidate: dict[str, tuple[DayName, int, str]],
        block_map: dict[str, PeriodBlock],
    ) -> list[TimetableEntry]:
        entries: list[TimetableEntry] = []
        for block_id, (day, period, room) in sorted(candidate.items(), key=lambda item: (item[1][0], item[1][1], item[0])):
            block = block_map[block_id]
            entries.append(
                TimetableEntry(
                    section=block.section,
                    day=day,
                    period=period,
                    course=block.subject,
                    room=room,
                    faculty_id=block.faculty_id,
                )
            )
        return entries

    def _compatible_rooms(self, block: PeriodBlock, rooms: list[RoomSpec]) -> list[str]:
        if block.kind == "LAB":
            lab_rooms = [room.name for room in rooms if room.is_lab]
            if lab_rooms:
                return lab_rooms
        return [room.name for room in rooms]
