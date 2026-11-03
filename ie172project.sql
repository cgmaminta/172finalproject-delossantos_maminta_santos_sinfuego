CREATE TYPE sex_enum AS ENUM ('Female', 'Male');

CREATE TABLE student(
	student_LRN serial primary key not null,
	student_name varchar(70) unique,
	student_age decimal(4,2),
	student_sex sex_enum,
	student_address varchar(90)
);


CREATE TABLE student (
    student_lrn          BIGINT PRIMARY KEY
                         CHECK (student_lrn BETWEEN 100000000000 AND 999999999999),
    student_last_name    VARCHAR(70) NOT NULL,
    student_first_name   VARCHAR(70) NOT NULL,
    student_middle_name  VARCHAR(70),
    student_age          NUMERIC(4,2),
    student_sex          sex_enum,
    student_address      VARCHAR(90),
    student_delete_ind   BOOLEAN DEFAULT FALSE
);


CREATE TABLE teacher(
	employee_id serial primary key not null,
	teacher_name varchar(70) unique
);
ALTER TABLE student
ADD student_delete_ind boolean not null default false;

ALTER TABLE teacher
ADD teacher_delete_ind boolean not null default false;

CREATE TABLE health_record(
	record_id serial primary key not null,
	student_LRN int REFERENCES student(student_LRN),
	record_date timestamp without time zone default now(),
	nutritional_status varchar(20),
	risk_status varchar(20),
	dietary_restrictions varchar(70),
	allergy varchar(70),
	height decimal(5,2),
	weight decimal(5,2),
	bmi decimal(4,2),
	z_score decimal(5,3)
);

CREATE TABLE program_cycle(
	cycle_id serial primary key not null,
	start_date timestamp without time zone default now(),
	end_date timestamp without time zone default now(),
	semester varchar(70)
);
CREATE TABLE program_enrolment (
	enrolment_id serial primary key not null,
	enrolment_date timestamp without time zone default now(),
	enrolment_status boolean not null default true,
	priority_level varchar(70),
	grade_level int,
	student_section varchar(70),
	employee_id int REFERENCES teacher(employee_id),
	cycle_id int REFERENCES program_cycle(cycle_id),
	student_LRN int REFERENCES student(student_LRN)
);

CREATE TABLE meal_plan (
    plan_id serial primary key not null,
    meal_type varchar(70),
	budget decimal(10,2),
	number_of_servings int,
    effective_date timestamp without time zone default now(),
    plan_delete_ind boolean default false
);

CREATE TABLE daily_log (
	log_id serial primary key not null,
	log_date timestamp without time zone default now(),
	attendance_status boolean not null default true,
	enrolment_id int REFERENCES program_enrolment(enrolment_id),
	plan_id int REFERENCES meal_plan(plan_id)
);
CREATE TABLE users (
    user_id serial primary key not null,
    user_name varchar(32) unique,
	user_password varchar(64) not null,
	user_modified_on timestamp without time zone default now(),
    user_delete_ind boolean default false
);

-- ==========================================
-- 1. CREATE STUDENT CLASS TABLE
-- ==========================================

CREATE TABLE student_class (
    class_id SERIAL PRIMARY KEY,
    grade_level INTEGER NOT NULL,
    student_section VARCHAR(70) NOT NULL,
    cycle_id INTEGER REFERENCES program_cycle(cycle_id),
    employee_id INTEGER REFERENCES teacher(employee_id),
    class_delete_ind BOOLEAN DEFAULT FALSE
);


-- ==========================================
-- 2. ADD CLASS ID TO PROGRAM ENROLMENT
-- ==========================================

ALTER TABLE program_enrolment
ADD COLUMN class_id INTEGER REFERENCES student_class(class_id);

ALTER TABLE student_class
ADD COLUMN class_archive_ind BOOLEAN NOT NULL DEFAULT FALSE;

-- ============ LRN: serial -> BIGINT (no auto-numbering) ============
ALTER TABLE student ALTER COLUMN student_lrn DROP DEFAULT;
ALTER TABLE student ALTER COLUMN student_lrn TYPE BIGINT;
DROP SEQUENCE IF EXISTS student_student_lrn_seq;

-- The enrolment foreign key must match the new type
ALTER TABLE program_enrolment ALTER COLUMN student_lrn TYPE BIGINT;

-- ============ Names: three separate columns ============

-- ---- Option A: existing rows are test data ----
DELETE FROM program_enrolment;
DELETE FROM student;

ALTER TABLE student
    DROP COLUMN student_name,
    ADD COLUMN student_last_name   VARCHAR(70) NOT NULL,
    ADD COLUMN student_first_name  VARCHAR(70) NOT NULL,
    ADD COLUMN student_middle_name VARCHAR(70);

-- ---- Option B: keep existing rows (use this INSTEAD of Option A) ----
-- ALTER TABLE student
--     ADD COLUMN student_last_name   VARCHAR(70),
--     ADD COLUMN student_first_name  VARCHAR(70),
--     ADD COLUMN student_middle_name VARCHAR(70);
--
-- UPDATE student
-- SET student_last_name  = TRIM(SPLIT_PART(student_name, ',', 1)),
--     student_first_name = TRIM(SPLIT_PART(student_name, ',', 2));
--
-- ALTER TABLE student
--     ALTER COLUMN student_last_name  SET NOT NULL,
--     ALTER COLUMN student_first_name SET NOT NULL;
--
-- ALTER TABLE student DROP COLUMN student_name;

-- ============ Enforce a 12-digit LRN ============
-- (Option B users: fix any rows with non-12-digit LRNs first)
ALTER TABLE student
    ADD CONSTRAINT student_lrn_12_digits
    CHECK (student_lrn BETWEEN 100000000000 AND 999999999999);


SELECT conrelid::regclass AS table_name, conname AS constraint_name
FROM pg_constraint
WHERE confrelid = 'student'::regclass
  AND contype = 'f';

DO $$
DECLARE
    r record;
BEGIN
    FOR r IN
        SELECT c.conrelid::regclass AS tbl,
               c.conname,
               pg_get_constraintdef(c.oid) AS def
        FROM pg_constraint c
        WHERE c.confrelid = 'student'::regclass
          AND c.contype = 'f'
          AND pg_get_constraintdef(c.oid) NOT LIKE '%ON UPDATE%'
    LOOP
        EXECUTE format('ALTER TABLE %s DROP CONSTRAINT %I', r.tbl, r.conname);
        EXECUTE format(
            'ALTER TABLE %s ADD CONSTRAINT %I %s ON UPDATE CASCADE',
            r.tbl, r.conname, r.def
        );
    END LOOP;
END $$;
SELECT conrelid::regclass AS table_name,
       conname AS constraint_name,
       CASE confupdtype WHEN 'c' THEN 'CASCADE' ELSE 'not cascade' END AS update_rule
FROM pg_constraint
WHERE confrelid = 'student'::regclass
  AND contype = 'f';