# AI-Based Timetable Automation & Smart Suggestion System
## Multi-Tenant Software Plan

## 1) Planning Assumptions
- The phrase **"multi tent"** is interpreted as **multi-tenant** (single platform for multiple institutions/campuses with data isolation).
- Tenants can represent an institution, group, or campus cluster.
- A web-first architecture is required, with responsive UI for desktop/mobile.

---

## 2) Product Vision
Build a **multi-tenant timetable intelligence platform** that:
1. Automates timetable generation under institutional constraints.
2. Detects and resolves clashes in real time.
3. Recommends AI-backed optimizations.
4. Supports simulations, emergency rescheduling, and quality scoring.
5. Integrates with ERP, LMS, attendance, and payroll systems.

---

## 3) Tenant Model & Data Isolation

### 3.1 Multi-Tenant Strategy
Use **shared application + shared database with tenant_id column** for fast rollout and lower cost, with optional upgrade path to isolated DB per premium tenant.

### 3.2 Tenant Hierarchy (Rewritten)
- `Tenant` (University Group / Trust / Parent Organization)
- `Campus` **or** `Institute` (Institute Name)
- `Department`
- `Program`
- `Section`

**Example path:** `Tenant: ABC Education Trust -> Institute: ABC College of Engineering -> Department: CSE -> Program: B.Tech -> Section: A`.

### 3.3 Isolation & Security
- Every business table includes `tenant_id`.
- Global query middleware enforces tenant filter.
- JWT/session token must carry `tenant_id` and role.
- Row-level access policy to block cross-tenant leakage.
- Tenant-specific encryption keys for sensitive data (optional phase-2 hardening).

---

## 4) Target Architecture (High Level)

### 4.1 Core Modules
1. **Auth & RBAC Service** (FR-1 to FR-4)
2. **Master Data Service** (FR-5 to FR-10)
3. **Constraint Engine** (FR-11 to FR-16)
4. **Scheduling Engine** (FR-17 to FR-21)
5. **AI Suggestion Engine** (FR-22 to FR-27)
6. **Conflict Detection Engine** (FR-28 to FR-32)
7. **Simulation Engine** (FR-33 to FR-37)
8. **Emergency Rescheduler** (FR-38 to FR-42)
9. **Quality Score Engine** (FR-43 to FR-47)
10. **Publishing & Notification Service** (FR-48 to FR-51)
11. **Analytics & Reporting** (FR-52 to FR-55)
12. **Integration API Gateway** (FR-56 to FR-59)

### 4.2 Suggested Deployment
- Frontend: React/Next.js
- Backend: Python (FastAPI) or Node.js (NestJS)
- DB: PostgreSQL
- Cache/queue: Redis + RabbitMQ/Kafka
- AI/Optimization worker: Python workers (OR-Tools + ML models)
- Object storage: S3-compatible
- Infra: Docker + Kubernetes

---

## 5) Domain Model (Core Entities)

### 5.1 Identity & Access
- Tenant
- User
- Role
- Permission
- UserRole
- SessionAudit

### 5.1A Multi-Level Access Provision (Added)
**Status: AVAILABLE (must be implemented).**

The system must support hierarchical access scopes so users can be restricted to one or more levels:
- **Group/Tenant Level** (whole group view/control across all institutes/campuses under the tenant)
- **Institute/Campus Level**
- **Department Level**
- **Program Level**
- **Section Level**

### 5.1B Access Scope Model
Use policy tuple:
- `user_id`
- `role_id`
- `tenant_id`
- `scope_type` in (`TENANT`, `INSTITUTE`, `DEPARTMENT`, `PROGRAM`, `SECTION`)
- `scope_id`
- `can_view`, `can_edit`, `can_approve`, `can_publish`

A user may have multiple scope assignments (example: HOD for one department and reviewer at institute level).

### 5.1C Minimum Role-to-Scope Mapping
- **Super Admin** -> Tenant scope
- **Institute Admin / Principal Office** -> Institute scope
- **HOD** -> Department scope
- **Program Coordinator** -> Program scope
- **Section Coordinator / Class In-charge** -> Section scope
- **Faculty** -> Section/program read-only (as assigned)

### 5.1D Enforcement Rules
- Every API call must validate both role permission and scope membership.
- Query filters must apply `tenant_id` + scoped entity filters before data retrieval.
- Approval/publish actions must be blocked if user scope is below required level.
- Audit logs must store effective scope used for each critical action.

### 5.2 Academic Master Data
- AcademicYear
- Semester
- Campus
- Department
- Program
- Section
- Course/Subject
- Faculty
- Room (classroom/lab)
- TimeSlot
- RegulationPolicy

### 5.3 Scheduling
- ConstraintDefinition
- TimetableDraft
- TimetableVersion
- TimetableEntry
- ConflictRecord
- SuggestionRecord
- SimulationScenario
- SimulationResult
- QualityScore
- PublishJob
- NotificationLog

All above entities must include `tenant_id`, `created_at`, `updated_at`, and soft-delete metadata where required.

---

## 6) Functional Delivery Plan (Phased)

## Phase 0: Foundation (2–3 weeks)
- Multi-tenant project bootstrap.
- Auth + RBAC baseline.
- Tenant onboarding and admin console.
- CI/CD + observability baseline.

**Exit criteria:** Secure tenant login and isolated tenant-level CRUD operational.

## Phase 1: Master Data + Constraints (3–4 weeks)
- Implement FR-5 to FR-16.
- Configurable rule templates per department.
- Validation UI for missing/inconsistent data.

**Exit criteria:** Complete tenant-specific data setup required for timetable generation.

## Phase 2: Scheduling + Conflict Core (4–6 weeks)
- Implement FR-17 to FR-21 and FR-28 to FR-32.
- Constraint solver integration (hard/soft constraints).
- Draft/final versioning.

**Exit criteria:** Timetable generation <= 30 sec for standard workload and clash visualization.

## Phase 3: AI Suggestions + Quality Score (4–5 weeks)
- Implement FR-22 to FR-27 and FR-43 to FR-47.
- Heuristic + explainable recommendation engine.
- Quality score dashboards and trend lines.

**Exit criteria:** Suggestion panel with measurable score improvements.

## Phase 4: Simulation + Emergency Reschedule (3–4 weeks)
- Implement FR-33 to FR-42.
- What-if scenarios and side-by-side comparison.
- Leave/substitute/reslot workflows with minimal disruption algorithm.

**Exit criteria:** Scenario simulation and emergency actions without mutating live schedule.

## Phase 5: Publish, Integrations, Analytics (3–5 weeks)
- Implement FR-48 to FR-59.
- PDF/Excel export.
- Notification center (email/SMS/app push).
- ERP/LMS/attendance/payroll connectors.

**Exit criteria:** End-to-end publish and sync flows live.

---

## 7) Scheduling & AI Engine Strategy

### 7.1 Constraint Types
- **Hard constraints:** no faculty clash, no room clash, capacity fit, lab continuity.
- **Soft constraints:** faculty preferences, fatigue reduction, idle-hour minimization.

### 7.2 Optimization Approach
- Model as weighted CSP/ILP.
- Objective function:
  - minimize clashes (hard → infeasible disallowed)
  - minimize faculty overload variance
  - minimize student fatigue score
  - maximize room utilization balance
  - minimize idle gaps

### 7.3 Suggestion Generation
- Local search + swap proposals.
- For each suggestion provide:
  - expected score delta
  - conflicts added/removed
  - affected stakeholders
  - rollback option

---

## 8) Non-Functional Execution Plan

### 8.1 Performance
- Precompute slot indices per tenant.
- Parallel worker pool for generation.
- Cache static master data.
- Incremental re-schedule for localized edits.

### 8.2 Security
- Password hashing (Argon2/bcrypt).
- TLS everywhere.
- AES encryption for sensitive columns.
- Audit trail for timetable changes and approvals.

### 8.3 Scalability
- Tenant-aware horizontal scaling.
- Worker autoscaling by queue depth.
- Sharding/DB split path for high-volume tenants.

### 8.4 Reliability
- 99.5% uptime target with health checks.
- Backups + PITR.
- Chaos/resilience drills for queue/DB outage.

---

## 9) API Blueprint (Sample)
- `POST /api/v1/auth/login`
- `GET /api/v1/master/subjects`
- `POST /api/v1/constraints`
- `POST /api/v1/timetables/generate`
- `GET /api/v1/timetables/{id}/conflicts`
- `POST /api/v1/timetables/{id}/suggestions`
- `POST /api/v1/simulations`
- `POST /api/v1/reschedule/emergency`
- `POST /api/v1/timetables/{id}/publish`
- `GET /api/v1/reports/faculty-workload`

All endpoints must enforce tenant context from token and request scope.

---

## 10) UI Plan

### 10.1 Core Screens
1. Tenant-aware login and role dashboard.
2. Master data setup wizard.
3. Constraint configuration studio.
4. Generation monitor + conflict heatmap.
5. AI suggestions panel (with impact preview).
6. Simulation workspace.
7. Emergency rescheduling cockpit.
8. Quality score and analytics dashboards.
9. Publish center + communication logs.

### 10.2 UX Principles
- Conflict-first visualization.
- Explainable AI suggestions.
- One-click rollback for risky changes.
- Mobile-friendly read-only timetable access.

---

## 11) Testing Strategy
- Unit tests for rule validators and scorers.
- Property-based tests for conflict detector.
- Integration tests for generate → detect → suggest → publish flow.
- Load tests per tenant and mixed-tenant concurrency.
- Security tests for tenant isolation and RBAC bypass attempts.
- UAT by role: coordinator, HOD, admin, faculty.

---

## 11A) NAAC/NBA Binary Compliance Criteria (Added)

To support accreditation readiness, introduce a **binary compliance layer** (`1 = compliant`, `0 = non-compliant`) for timetable governance and audit reporting.

### 11A.1 Binary Criteria Set
| Code | Criterion | Binary Rule (1/0) | Evidence Source |
|---|---|---|---|
| NB-01 | Faculty clash-free timetable | 1 if no faculty overlaps in published version | Conflict engine logs |
| NB-02 | Room clash-free timetable | 1 if no room overlaps in published version | Conflict engine logs |
| NB-03 | Lab continuity compliance | 1 if configured continuous lab rules are satisfied | Constraint validation report |
| NB-04 | Faculty workload within limit | 1 if all faculty are within defined daily/weekly max load | Workload analytics |
| NB-05 | Minimum timetable quality threshold | 1 if quality index >= tenant-defined threshold | Quality score engine |
| NB-06 | Timetable approval workflow completed | 1 if coordinator + HOD approval steps completed | Approval audit logs |
| NB-07 | Publish + communication completed | 1 if timetable is published and notifications sent | Publish + notification logs |
| NB-08 | Emergency changes audited | 1 if all emergency reschedules include reason and approver | Reschedule audit logs |
| NB-09 | Data freshness and version traceability | 1 if active version has complete version metadata | Timetable version history |
| NB-10 | Tenant-level isolation verified | 1 if no cross-tenant access violations detected | Security/audit monitoring |

### 11A.2 Compliance Scoring
- **Binary Score (%)** = `(sum of passed criteria / total criteria) * 100`.
- Status bands:
  - `>= 90%`: Accreditation-ready (Green)
  - `75% to 89%`: Needs minor corrective actions (Amber)
  - `< 75%`: Major compliance risk (Red)

### 11A.3 Reporting Requirements
- Add monthly **NAAC/NBA Compliance Snapshot** per tenant/campus.
- Include criterion-wise pass/fail trend for last 6 months.
- Provide downloadable PDF/Excel evidence bundle linked to each binary criterion.

---

## 12) DevOps & Delivery
- Branch strategy + PR checks.
- CI pipeline: lint, unit tests, integration tests.
- CD pipeline with staging and production gates.
- Feature flags for module-wise rollout.
- Migration strategy with backward compatibility.

---

## 13) Milestones & Timeline (Indicative ~20–27 weeks)
- M1: Foundation complete
- M2: Master + constraints complete
- M3: Generation + conflict complete
- M4: AI suggestions + quality complete
- M5: Simulation + emergency complete
- M6: Publish + integrations + analytics complete

---

## 14) Risks & Mitigation
1. **Poor master data quality** → validation gates + onboarding checklist.
2. **Solver latency for large campuses** → partitioning + heuristic warm start.
3. **User resistance to automation** → explainable suggestions + manual override.
4. **Integration instability** → retry queues + API contracts + fallbacks.
5. **Cross-tenant data leak risk** → strict middleware + security tests + audits.

---

## 15) Immediate Next 10 Actions
1. Confirm tenant definition (institution vs campus).
2. Finalize MVP boundary (Phase 0–2).
3. Freeze role-permission matrix.
4. Approve canonical slot model (period/day/week).
5. Define hard vs soft constraints with weights.
6. Create DB schema with tenant_id and audit fields.
7. Build master data import templates.
8. Stand up basic timetable generation prototype.
9. Validate generation performance on sample data.
10. Launch pilot with one department and iterate.

