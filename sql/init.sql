
USE shard_db;

CREATE TABLE students (
    student_id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    department VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_replica BOOLEAN NOT NULL DEFAULT FALSE,
    primary_shard VARCHAR(100) NULL
);

CREATE INDEX idx_student_email
ON students(email);

CREATE INDEX idx_student_department
ON students(department);

CREATE INDEX idx_student_primary_replica ON students(is_replica, student_id);
