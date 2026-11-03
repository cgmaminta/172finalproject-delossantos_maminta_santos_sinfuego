
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
