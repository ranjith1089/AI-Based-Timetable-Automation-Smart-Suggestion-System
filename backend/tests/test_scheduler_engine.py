from app.scheduler.engine import preprocess, run_scheduler
from app.schemas import SchedulerAdminConfig, SchedulerSectionInput, SchedulerSubjectInput


def test_lab_continuity_blocks_created() -> None:
    sections = [
        SchedulerSectionInput(
            section="CSE-A",
            subjects=[
                SchedulerSubjectInput(
                    code="OS-LAB",
                    ltp="0-0-4",
                    faculty_id="F-LAB",
                    room_type="LAB",
                    lab_block_size=2,
                )
            ],
        )
    ]
    admin = SchedulerAdminConfig(
        working_days=["Monday", "Tuesday"],
        hours_per_day=4,
        allowed_lab_block_sizes=[2, 4],
        default_lab_block_size=2,
    )

    pre = preprocess(sections, admin)
    practical_tasks = [task for task in pre.tasks if task.kind == "P"]
    assert len(practical_tasks) == 2
    assert all(task.duration == 2 for task in practical_tasks)
    assert pre.preprocessing_conflicts == []


def test_overflow_handling_reports_unscheduled_tasks() -> None:
    sections = [
        SchedulerSectionInput(
            section="EEE-A",
            subjects=[
                SchedulerSubjectInput(code="M1", ltp="4-0-0", faculty_id="F1"),
                SchedulerSubjectInput(code="M2", ltp="4-0-0", faculty_id="F2"),
                SchedulerSubjectInput(code="M3", ltp="4-0-0", faculty_id="F3"),
            ],
        )
    ]
    admin = SchedulerAdminConfig(working_days=["Monday"], hours_per_day=4)

    result = run_scheduler(
        tenant_id="t-overflow",
        sections=sections,
        rooms=["R1"],
        room_types={"R1": "CLASSROOM"},
        admin=admin,
        population_size=8,
        generations=8,
    )

    assert result.constraint_summary["exact_weekly_fulfillment"] is False
    assert result.conflict_count > 0
    assert any("Unable to place task" in conflict.message for conflict in result.conflicts)


def test_multi_section_clash_avoidance_for_elective_sync() -> None:
    sections = [
        SchedulerSectionInput(
            section="CSE-A",
            subjects=[
                SchedulerSubjectInput(
                    code="EL-1",
                    ltp="1-0-0",
                    faculty_id="F-E1",
                    elective_group="ELECTIVE-X",
                )
            ],
        ),
        SchedulerSectionInput(
            section="CSE-B",
            subjects=[
                SchedulerSubjectInput(
                    code="EL-1",
                    ltp="1-0-0",
                    faculty_id="F-E2",
                    elective_group="ELECTIVE-X",
                )
            ],
        ),
    ]
    admin = SchedulerAdminConfig(working_days=["Monday", "Tuesday"], hours_per_day=3)

    result = run_scheduler(
        tenant_id="t-sync",
        sections=sections,
        rooms=["R1", "R2"],
        room_types={"R1": "CLASSROOM", "R2": "CLASSROOM"},
        admin=admin,
        population_size=10,
        generations=10,
    )

    a_entry = next(entry for entry in result.timetable if entry.section == "CSE-A")
    b_entry = next(entry for entry in result.timetable if entry.section == "CSE-B")
    assert (a_entry.day, a_entry.period) == (b_entry.day, b_entry.period)
    assert not any(conflict.conflict_type == "SECTION" for conflict in result.conflicts)
