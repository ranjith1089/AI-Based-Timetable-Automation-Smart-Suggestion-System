CREATE TABLE tenants (
  tenant_id VARCHAR(64) PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE institutes (
  institute_id VARCHAR(64) PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
  name VARCHAR(255) NOT NULL
);

CREATE TABLE departments (
  department_id VARCHAR(64) PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
  institute_id VARCHAR(64) NOT NULL REFERENCES institutes(institute_id),
  name VARCHAR(255) NOT NULL
);

CREATE TABLE programs (
  program_id VARCHAR(64) PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
  department_id VARCHAR(64) NOT NULL REFERENCES departments(department_id),
  name VARCHAR(255) NOT NULL
);

CREATE TABLE sections (
  section_id VARCHAR(64) PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
  program_id VARCHAR(64) NOT NULL REFERENCES programs(program_id),
  name VARCHAR(255) NOT NULL
);

CREATE TABLE users (
  user_id VARCHAR(64) PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE roles (
  role_id VARCHAR(64) PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
  role_name VARCHAR(100) NOT NULL
);

CREATE TABLE user_roles (
  user_id VARCHAR(64) NOT NULL REFERENCES users(user_id),
  role_id VARCHAR(64) NOT NULL REFERENCES roles(role_id),
  PRIMARY KEY (user_id, role_id)
);

CREATE TABLE access_scopes (
  scope_pk BIGSERIAL PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL REFERENCES users(user_id),
  role_id VARCHAR(64) NOT NULL REFERENCES roles(role_id),
  tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
  scope_type VARCHAR(20) NOT NULL CHECK (scope_type IN ('TENANT', 'INSTITUTE', 'DEPARTMENT', 'PROGRAM', 'SECTION')),
  scope_id VARCHAR(64) NOT NULL,
  can_view BOOLEAN NOT NULL DEFAULT TRUE,
  can_edit BOOLEAN NOT NULL DEFAULT FALSE,
  can_approve BOOLEAN NOT NULL DEFAULT FALSE,
  can_publish BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE timetable_versions (
  version_id VARCHAR(64) PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
  status VARCHAR(20) NOT NULL CHECK (status IN ('DRAFT', 'FINAL', 'PUBLISHED')),
  quality_score NUMERIC(5,2) NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE timetable_entries (
  entry_id BIGSERIAL PRIMARY KEY,
  version_id VARCHAR(64) NOT NULL REFERENCES timetable_versions(version_id),
  tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
  section_id VARCHAR(64) NOT NULL REFERENCES sections(section_id),
  day_of_week VARCHAR(20) NOT NULL,
  period_no INT NOT NULL,
  subject_name VARCHAR(255) NOT NULL,
  faculty_name VARCHAR(255) NOT NULL,
  room_name VARCHAR(255) NOT NULL
);

CREATE TABLE faculty_availability (
  availability_id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
  faculty_id VARCHAR(64) NOT NULL,
  slot_key VARCHAR(64) NOT NULL,
  is_available BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE subjects (
  subject_id VARCHAR(64) PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
  name VARCHAR(255) NOT NULL,
  credits INT NOT NULL DEFAULT 3,
  is_lab BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE rooms (
  room_id VARCHAR(64) PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
  room_name VARCHAR(255) NOT NULL,
  capacity INT NOT NULL,
  room_type VARCHAR(20) NOT NULL CHECK (room_type IN ('CLASSROOM', 'LAB'))
);

CREATE TABLE timeslots (
  slot_id VARCHAR(64) PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
  day_of_week VARCHAR(20) NOT NULL,
  period_no INT NOT NULL,
  UNIQUE (tenant_id, day_of_week, period_no)
);

CREATE TABLE constraint_rules (
  rule_id VARCHAR(64) PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
  name VARCHAR(255) NOT NULL,
  category VARCHAR(10) NOT NULL CHECK (category IN ('HARD', 'SOFT')),
  weight INT NOT NULL CHECK (weight >= 1 AND weight <= 100),
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  params JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE timetable_conflicts (
  conflict_id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
  version_id VARCHAR(64) NOT NULL REFERENCES timetable_versions(version_id),
  conflict_type VARCHAR(20) NOT NULL,
  section_id VARCHAR(64),
  day_of_week VARCHAR(20) NOT NULL,
  period_no INT NOT NULL,
  message TEXT NOT NULL
);

CREATE TABLE timetable_suggestions (
  suggestion_id VARCHAR(64) PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
  version_id VARCHAR(64) NOT NULL REFERENCES timetable_versions(version_id),
  suggestion_type VARCHAR(30) NOT NULL,
  description TEXT NOT NULL,
  expected_quality_delta NUMERIC(5,2) NOT NULL
);

CREATE TABLE simulation_scenarios (
  scenario_id VARCHAR(64) PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
  scenario_name VARCHAR(255) NOT NULL,
  scenario_type VARCHAR(30) NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE simulation_results (
  result_id BIGSERIAL PRIMARY KEY,
  scenario_id VARCHAR(64) NOT NULL REFERENCES simulation_scenarios(scenario_id),
  tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
  impact_summary TEXT NOT NULL,
  estimated_conflicts INT NOT NULL,
  estimated_quality_score NUMERIC(5,2) NOT NULL
);

CREATE TABLE emergency_reschedules (
  reschedule_id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
  reason TEXT NOT NULL,
  affected_faculty_id VARCHAR(64) NOT NULL,
  substitute_faculty_id VARCHAR(64),
  section_id VARCHAR(64),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE quality_scores (
  score_id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
  version_id VARCHAR(64) NOT NULL REFERENCES timetable_versions(version_id),
  faculty_load_balance NUMERIC(5,2) NOT NULL,
  student_fatigue NUMERIC(5,2) NOT NULL,
  room_utilization NUMERIC(5,2) NOT NULL,
  clash_risk NUMERIC(5,2) NOT NULL,
  overall_quality NUMERIC(5,2) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tt_entries_section_slot
  ON timetable_entries (tenant_id, section_id, day_of_week, period_no);

CREATE INDEX idx_tt_entries_room_slot
  ON timetable_entries (tenant_id, room_name, day_of_week, period_no);

CREATE INDEX idx_faculty_availability_slot
  ON faculty_availability (tenant_id, faculty_id, slot_key);
