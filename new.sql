
-- ==========================================
-- 1. CREATE ENUM TYPE
-- ==========================================

CREATE TYPE sex_enum AS ENUM ('Female', 'Male');


-- ==========================================
-- 2. CREATE STUDENT TABLE
-- ==========================================

CREATE TABLE student (
    student_lrn BIGINT PRIMARY KEY
        CHECK (student_lrn BETWEEN 100000000000 AND 999999999999),

    student_last_name VARCHAR(70) NOT NULL,
    student_first_name VARCHAR(70) NOT NULL,
    student_middle_name VARCHAR(70),

    student_age NUMERIC(4,2),
    student_sex sex_enum,
    student_address VARCHAR(90),

    student_delete_ind BOOLEAN NOT NULL DEFAULT FALSE
);


-- ==========================================
-- 3. CREATE TEACHER TABLE
-- ==========================================

CREATE TABLE teacher (
    employee_id SERIAL PRIMARY KEY,
    teacher_name VARCHAR(70) UNIQUE,

    teacher_delete_ind BOOLEAN NOT NULL DEFAULT FALSE
);


-- ==========================================
-- 4. CREATE HEALTH RECORD TABLE
-- ==========================================

CREATE TABLE health_record (
    record_id SERIAL PRIMARY KEY,

    student_lrn BIGINT REFERENCES student(student_lrn)
        ON UPDATE CASCADE,

    record_date TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    nutritional_status VARCHAR(20),
    risk_status VARCHAR(20),
    dietary_restrictions VARCHAR(70),
    allergy VARCHAR(70),

    height NUMERIC(5,2),
    weight NUMERIC(5,2),
    bmi NUMERIC(4,2),
    z_score NUMERIC(5,3)
);


-- ==========================================
-- 5. CREATE PROGRAM CYCLE TABLE
-- ==========================================

CREATE TABLE program_cycle (
    cycle_id SERIAL PRIMARY KEY,

    start_date TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    end_date TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),

    semester VARCHAR(70)
);


-- ==========================================
-- 6. CREATE STUDENT CLASS TABLE
-- ==========================================

CREATE TABLE student_class (
    class_id SERIAL PRIMARY KEY,

    grade_level INTEGER NOT NULL,
    student_section VARCHAR(70) NOT NULL,

    cycle_id INTEGER REFERENCES program_cycle(cycle_id),
    employee_id INTEGER REFERENCES teacher(employee_id),

    class_delete_ind BOOLEAN NOT NULL DEFAULT FALSE,
    class_archive_ind BOOLEAN NOT NULL DEFAULT FALSE
);


-- ==========================================
-- 7. CREATE PROGRAM ENROLMENT TABLE
-- ==========================================

CREATE TABLE program_enrolment (
    enrolment_id SERIAL PRIMARY KEY,

    enrolment_date TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    enrolment_status BOOLEAN NOT NULL DEFAULT TRUE,

    priority_level VARCHAR(70),
    grade_level INTEGER,
    student_section VARCHAR(70),

    employee_id INTEGER REFERENCES teacher(employee_id),
    cycle_id INTEGER REFERENCES program_cycle(cycle_id),
    student_lrn BIGINT REFERENCES student(student_lrn)
        ON UPDATE CASCADE,
    class_id INTEGER REFERENCES student_class(class_id)
);


-- ==========================================
-- 8. CREATE MEAL PLAN TABLE
-- ==========================================

CREATE TABLE meal_plan (
    plan_id SERIAL PRIMARY KEY,

    meal_type VARCHAR(70),
    budget NUMERIC(10,2),
    number_of_servings INTEGER,

    effective_date TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),

    plan_delete_ind BOOLEAN NOT NULL DEFAULT FALSE
);


-- ==========================================
-- 9. CREATE DAILY LOG TABLE
-- ==========================================

CREATE TABLE daily_log (
    log_id SERIAL PRIMARY KEY,

    log_date TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    attendance_status BOOLEAN NOT NULL DEFAULT TRUE,

    enrolment_id INTEGER REFERENCES program_enrolment(enrolment_id),
    plan_id INTEGER REFERENCES meal_plan(plan_id)
);


-- ==========================================
-- 10. CREATE USERS TABLE
-- ==========================================

CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,

    user_name VARCHAR(32) UNIQUE,
    user_password VARCHAR(255) NOT NULL,

    user_modified_on TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),

    user_delete_ind BOOLEAN NOT NULL DEFAULT FALSE
);


-- ==========================================
-- FIX STUDENT LRN DATA TYPES
-- ==========================================

-- Step 1: Drop the existing foreign keys

ALTER TABLE health_record
DROP CONSTRAINT IF EXISTS health_record_student_lrn_fkey;

ALTER TABLE program_enrolment
DROP CONSTRAINT IF EXISTS program_enrolment_student_lrn_fkey;


-- Step 2: Change both referencing columns to BIGINT

ALTER TABLE health_record
ALTER COLUMN student_lrn TYPE BIGINT;

ALTER TABLE program_enrolment
ALTER COLUMN student_lrn TYPE BIGINT;


-- Step 3: Recreate the foreign keys with ON UPDATE CASCADE

ALTER TABLE health_record
ADD CONSTRAINT health_record_student_lrn_fkey
FOREIGN KEY (student_lrn)
REFERENCES student(student_lrn)
ON UPDATE CASCADE;

ALTER TABLE program_enrolment
ADD CONSTRAINT program_enrolment_student_lrn_fkey
FOREIGN KEY (student_lrn)
REFERENCES student(student_lrn)
ON UPDATE CASCADE;
