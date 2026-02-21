-- MySQL initialization script for SchoolApp
-- This script runs when the MySQL container starts for the first time

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS multi_sis_database CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Grant privileges to the application user
GRANT ALL PRIVILEGES ON multi_sis_database.* TO 'sis_user'@'%';
FLUSH PRIVILEGES;

-- Set default character set
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;
SET character_set_connection=utf8mb4;



