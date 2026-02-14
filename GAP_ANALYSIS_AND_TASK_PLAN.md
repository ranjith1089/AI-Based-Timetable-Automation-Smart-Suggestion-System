# Gap Analysis & Task Plan
## AI-Based Timetable Automation and Smart Suggestions for Timetable Coordinators

## 1) Executive Summary
Current repository status is a **Phase-0 scaffold** (UI shell + basic API + starter DB schema + smoke tests). It is **not yet feature-complete** for timetable coordinators.

Your requested coordinator-centric capabilities (constraint-based generation, AI suggestions, conflict prevention, simulation, emergency rescheduling, quality score, and integrations) are mostly **missing at implementation level** and need structured delivery.

---

## 2) Current System vs Required Capabilities (Comparison)

### 2.1 What Exists Today
- Frontend: single dashboard scaffold with static cards.
- Backend: basic endpoints (`/health`, `/users`, `/access/scope`, `/timetables/generate`).
- Timetable generation: placeholder round-robin assignment (no solver).
- Database: core tenant hierarchy + RBAC + timetable tables.
- Testing: basic API tests only.

### 2.2 Gap Matrix
| Feature Area | Needed for Coordinator | Current Status | Gap |
|---|---|---|---|
| Smart constraint engine | Faculty availability, lab continuity, room capacity, workload limits, regulations | Not implemented | Critical |
| AI suggestions | Split load, swap periods, idle-room reduction, fatigue reduction | Not implemented | Critical |
| Load balancing | Faculty overload/underload analysis and recommendations | Not implemented | High |
| Real-time conflict detection | Faculty/room/lab/cross-dept alerts before save | Not implemented | Critical |
| What-if simulation | Scenario testing without affecting live timetable | Not implemented | Critical |
| Emergency rescheduling | Leave/event/holiday one-click alternatives | Not implemented | Critical |
| Preference/satisfaction layer | Faculty preferred slots, fairness balancing | Not implemented | Medium |
| Timetable quality score | Multi-factor scoring with drill-down | Placeholder static score only | High |
| Integrations | Attendance/payroll/LMS/exam sync | Not implemented | High |
| Coordinator UX workflow | Draft->review->approve->publish with explainability | Not implemented | Critical |

---

## 3) Missing Features to Add (Prioritized)

## P0 (Must Build First)
1. **Constraint Definition Module**
   - CRUD for constraints by tenant/institute/department.
   - Hard constraints + soft constraint weights.
2. **Conflict Detection Engine**
   - Validate clashes at create/update/save.
   - Return human-readable conflict reasons + highlighted entities.
3. **Real Scheduling Engine (v1)**
   - Replace placeholder generator with solver-based scheduling.
4. **Draft/Final/Published Version Workflow**
   - Approval states, role-gated transitions, audit trails.
5. **Coordinator Workbench UI**
   - Timetable grid, conflicts panel, rule panel, save/publish actions.

## P1 (High Value Next)
6. **AI Suggestion Engine v1**
   - Swap recommendations, overload split suggestions, idle slot optimization.
7. **Load Balance Analytics**
   - Faculty load variance and student heavy-day detection.
8. **What-if Simulation Mode**
   - Add/remove section/faculty, holiday insertion, 5-day week switch.
9. **Emergency Rescheduling**
   - Faculty leave and substitute recommendations with minimal disruption logic.
10. **Quality Score Engine**
    - Score dimensions: load balance, fatigue, utilization, clash risk, flexibility.

## P2 (Scale + Adoption)
11. **Preference & Satisfaction Layer**
12. **Integration Connectors (Attendance/LMS/Payroll/Exam)**
13. **NAAC/NBA evidence exports and scheduled compliance snapshot jobs**
14. **Explainability dashboard for AI decisions**

---

## 4) Detailed Task List by Layer

## 4.1 Backend Tasks
- Create modules:
  - `constraints`, `scheduler`, `conflicts`, `suggestions`, `simulations`, `rescheduler`, `quality`.
- Add endpoints:
  - `POST /constraints`, `GET /constraints`
  - `POST /timetables/validate`
  - `POST /timetables/generate`
  - `POST /timetables/{id}/suggestions`
  - `POST /simulations`
  - `POST /reschedule/emergency`
  - `GET /timetables/{id}/quality`
- Add service layer:
  - constraint compiler
  - clash detector
  - scoring calculator
  - suggestion generator
- Add audit/event logs for each coordinator action.

## 4.2 Database Tasks
- Add new tables:
  - `constraint_rules`
  - `faculty_availability`
  - `rooms`
  - `subjects`
  - `timeslots`
  - `timetable_conflicts`
  - `timetable_suggestions`
  - `simulation_scenarios`
  - `simulation_results`
  - `emergency_reschedules`
  - `quality_scores`
- Add indexes:
  - `(tenant_id, section_id, day_of_week, period_no)`
  - `(tenant_id, faculty_id, day_of_week, period_no)`
  - `(tenant_id, room_id, day_of_week, period_no)`
- Add versioning FK integrity + soft delete fields where required.

## 4.3 Frontend Tasks
- Build coordinator pages:
  - Master setup (faculty, rooms, subjects, slots)
  - Constraint builder
  - Timetable editor/grid
  - Conflict panel (real-time)
  - Suggestions panel with apply/revert
  - Simulation workspace
  - Emergency reschedule wizard
  - Quality score dashboard
- UX enhancements:
  - color-coded clash highlights
  - side-by-side before/after comparison
  - one-click rollback of suggestion applications

## 4.4 Testing Tasks
- Unit tests:
  - constraint validation
  - conflict detection
  - quality score math
- Integration tests:
  - rule setup -> generate -> detect -> suggest -> publish
- Scenario tests:
  - faculty leave
  - added section
  - room outage
- Performance tests:
  - generation latency under realistic tenant load
- Security tests:
  - tenant isolation and scope escalation attempts

---

## 5) Delivery Plan (12-Week Practical Roadmap)

### Sprint 1-2 (Weeks 1-2)
- DB migrations for master data + constraints + conflicts
- backend CRUD for master data
- starter coordinator UI for master setup

### Sprint 3-4 (Weeks 3-4)
- implement hard-constraint validator
- realtime conflict APIs + frontend conflict rendering
- draft timetable workflow

### Sprint 5-6 (Weeks 5-6)
- solver-based generation v1
- publish workflow + approvals + audit logs
- integration tests for generate pipeline

### Sprint 7-8 (Weeks 7-8)
- AI suggestions v1 (swap, split, idle optimization)
- suggestion impact preview and apply/revert actions

### Sprint 9-10 (Weeks 9-10)
- what-if simulation workspace and result comparison
- emergency rescheduling workflow

### Sprint 11-12 (Weeks 11-12)
- quality score engine and dashboard
- compliance exports (NAAC/NBA evidence bundle)
- performance hardening and release readiness

---

## 6) Acceptance Criteria (Coordinator Success)
1. Coordinator can define constraints once and regenerate schedules quickly.
2. No timetable can be published with unresolved hard conflicts.
3. AI suggestions are explainable and reversible.
4. What-if simulations do not modify live published timetable.
5. Emergency reschedule completes in <= 2 minutes for common leave/event cases.
6. Quality score and compliance report can be exported per tenant/institute.

---

## 7) Immediate Next 15 Engineering Tasks (Actionable)
1. Finalize canonical period/slot data model.
2. Add DB migration framework (Alembic) and baseline migration.
3. Implement faculty/room/subject/time slot APIs.
4. Implement constraint CRUD + priority weights.
5. Build clash detection service and endpoint.
6. Integrate clash checks in save and publish actions.
7. Replace placeholder generation with solver adapter interface.
8. Add schedule version states and approval permissions.
9. Build frontend timetable grid and conflict badges.
10. Build suggestion API contract and frontend suggestion panel.
11. Add simulation scenario persistence and compare API.
12. Add emergency leave reschedule endpoint.
13. Add quality score computation endpoint.
14. Expand test suite to integration + performance tests.
15. Prepare pilot data and run coordinator UAT.

---

## 8) Recommended Product Packaging (for GTM)
- **Basic**: Rule-based generation + conflict detection.
- **Pro**: AI suggestions + load balancing + quality score.
- **Enterprise**: Simulation + emergency rescheduling + integrations + compliance exports.

This gives a practical upsell path while keeping first adoption fast for institutions.
