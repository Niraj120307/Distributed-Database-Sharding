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