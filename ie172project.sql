CREATE TYPE sex_enum AS ENUM ('Female', 'Male');

CREATE TABLE student(
	student_LRN serial primary key not null,
	student_name varchar(70) unique,
	student_age decimal(4,2),
	student_sex sex_enum,
	student_address varchar(90)
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