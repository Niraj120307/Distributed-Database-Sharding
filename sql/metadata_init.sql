USE cluster_metadata;

-- Stores information about database nodes
CREATE TABLE shard_nodes (

    node_id INT AUTO_INCREMENT PRIMARY KEY,

    node_name VARCHAR(100) NOT NULL UNIQUE,

    host VARCHAR(100) NOT NULL,

    port INT NOT NULL,

    database_name VARCHAR(100) NOT NULL,

    status ENUM('ACTIVE', 'INACTIVE')
        DEFAULT 'ACTIVE',

    virtual_nodes INT DEFAULT 100,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
);


-- Stores cluster-wide configuration
CREATE TABLE cluster_config (

    config_id INT AUTO_INCREMENT PRIMARY KEY,

    config_key VARCHAR(100) NOT NULL UNIQUE,

    config_value VARCHAR(255) NOT NULL,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS migration_jobs (
    job_id INT AUTO_INCREMENT PRIMARY KEY,
    strategy VARCHAR(32) NOT NULL,
    total_records INT NOT NULL DEFAULT 0,
    records_to_move INT NOT NULL DEFAULT 0,
    records_migrated INT NOT NULL DEFAULT 0,
    status ENUM('RUNNING','COMPLETED','FAILED') NOT NULL DEFAULT 'RUNNING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS migration_records (
    record_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    job_id INT NOT NULL,
    student_id INT NOT NULL,
    source_shard VARCHAR(100) NOT NULL,
    destination_shard VARCHAR(100) NOT NULL,
    status ENUM('SUCCESS','FAILED') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_migration_job (job_id),
    CONSTRAINT fk_migration_records_job FOREIGN KEY (job_id) REFERENCES migration_jobs(job_id)
);

CREATE TABLE IF NOT EXISTS operation_events (
    operation_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    operation VARCHAR(64) NOT NULL,
    target VARCHAR(128) NOT NULL,
    status ENUM('SUCCESS','FAILED') NOT NULL DEFAULT 'SUCCESS',
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_operation_time (occurred_at)
);
