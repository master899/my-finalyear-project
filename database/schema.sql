CREATE DATABASE tb_cdss;
USE tb_cdss;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'health_worker',
    can_add_user BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE screenings (
    id INT AUTO_INCREMENT PRIMARY KEY,

    patient_name VARCHAR(120) NOT NULL,
    age INT NOT NULL,
    gender VARCHAR(20) NOT NULL,

    cough BOOLEAN NOT NULL,
    cough_duration BOOLEAN NOT NULL,
    night_sweats BOOLEAN NOT NULL,
    weight_loss BOOLEAN NOT NULL,
    coughing_blood BOOLEAN NOT NULL,
    fever BOOLEAN NOT NULL,
    fatigue BOOLEAN NOT NULL,
    chest_pain BOOLEAN NOT NULL,

    risk_level VARCHAR(20) NOT NULL,
    recommendation TEXT NOT NULL,
    language_selected VARCHAR(20) NOT NULL DEFAULT 'en',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE permission_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,

    user_id INT NOT NULL,

    permission_type VARCHAR(50) NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'pending',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    reviewed_at DATETIME NULL,

    FOREIGN KEY (user_id) REFERENCES users(id)
);