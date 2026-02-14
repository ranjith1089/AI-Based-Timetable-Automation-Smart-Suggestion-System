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
