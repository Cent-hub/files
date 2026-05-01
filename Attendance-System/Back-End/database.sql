-- ============================================================
--  ATTENDANCE MANAGEMENT SYSTEM — DATABASE SCHEMA
--  Engine: MySQL 8.0+
-- ============================================================

CREATE DATABASE IF NOT EXISTS attendance_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE attendance_db;

-- ─────────────────────────────────────────
--  USERS  (students + teachers share table)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id             INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    full_name      VARCHAR(120)        NOT NULL,
    email          VARCHAR(180)        NULL,
    password       VARCHAR(255)        NOT NULL,   -- bcrypt hash
    role           ENUM('student','teacher') NOT NULL DEFAULT 'student',
    student_id     VARCHAR(30)         NULL UNIQUE,
    section        VARCHAR(50)         NULL,
    student_type   ENUM('regular','irregular') DEFAULT 'regular',
    gender         VARCHAR(20)         NULL,
    department     VARCHAR(100)        NULL,
    profile_picture TEXT               NULL,
    created_at     TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ─────────────────────────────────────────
--  SESSIONS  (class meetings / events)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    teacher_id  INT UNSIGNED        NOT NULL,
    subject     VARCHAR(120)        NOT NULL,
    section     VARCHAR(50)         NOT NULL,
    session_date DATE               NOT NULL,
    start_time  TIME                NOT NULL,
    end_time    TIME                NOT NULL,
    code        CHAR(6)             NOT NULL UNIQUE,   -- e.g. "ATT7X2"
    max_students INT UNSIGNED       NULL,             -- optional limit
    is_open     TINYINT(1)          NOT NULL DEFAULT 1,
    created_at  TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ─────────────────────────────────────────
--  ATTENDANCE RECORDS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS attendance (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id      INT UNSIGNED    NOT NULL,
    student_id      INT UNSIGNED    NOT NULL,
    confirmed_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status          ENUM('present','late','absent') NOT NULL DEFAULT 'present',
    UNIQUE KEY uq_session_student (session_id, student_id),
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES users(id)    ON DELETE CASCADE
) ENGINE=InnoDB;


