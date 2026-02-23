BEGIN;

CREATE TABLE IF NOT EXISTS semesters (
  semester_id VARCHAR(64) PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
  program_id VARCHAR(64) NOT NULL REFERENCES programs(program_id),
  name VARCHAR(100) NOT NULL,
  sequence_no INT NOT NULL CHECK (sequence_no >= 1),
  UNIQUE (tenant_id, program_id, sequence_no),
  UNIQUE (tenant_id, program_id, name)
);

ALTER TABLE subjects
  ADD COLUMN IF NOT EXISTS program_id VARCHAR(64),
  ADD COLUMN IF NOT EXISTS semester_id VARCHAR(64),
  ADD COLUMN IF NOT EXISTS regulation VARCHAR(64),
  ADD COLUMN IF NOT EXISTS course_code VARCHAR(64),
  ADD COLUMN IF NOT EXISTS course_type VARCHAR(20),
  ADD COLUMN IF NOT EXISTS l_hours INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS t_hours INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS p_hours INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS tcp INT NOT NULL DEFAULT 0;

ALTER TABLE subjects
  ADD CONSTRAINT chk_subject_l_hours_non_negative CHECK (l_hours >= 0),
  ADD CONSTRAINT chk_subject_t_hours_non_negative CHECK (t_hours >= 0),
  ADD CONSTRAINT chk_subject_p_hours_non_negative CHECK (p_hours >= 0),
  ADD CONSTRAINT chk_subject_tcp_non_negative CHECK (tcp >= 0);

ALTER TABLE subjects
  ADD CONSTRAINT fk_subjects_program FOREIGN KEY (program_id) REFERENCES programs(program_id),
  ADD CONSTRAINT fk_subjects_semester FOREIGN KEY (semester_id) REFERENCES semesters(semester_id),
  ADD CONSTRAINT chk_subject_course_type CHECK (course_type IN ('THEORY', 'PRACTICAL', 'TUTORIAL', 'PROJECT'));

ALTER TABLE subjects
  ADD CONSTRAINT uq_subjects_course_code_scope UNIQUE (tenant_id, program_id, regulation, semester_id, course_code),
  ADD CONSTRAINT uq_subjects_name_scope UNIQUE (tenant_id, program_id, regulation, semester_id, name);

ALTER TABLE timetable_entries
  ADD COLUMN IF NOT EXISTS subject_id VARCHAR(64);

ALTER TABLE timetable_entries
  ADD CONSTRAINT fk_timetable_entries_subject FOREIGN KEY (subject_id) REFERENCES subjects(subject_id);

CREATE INDEX IF NOT EXISTS idx_tt_entries_subject_slot
  ON timetable_entries (tenant_id, subject_id, day_of_week, period_no);

COMMIT;
