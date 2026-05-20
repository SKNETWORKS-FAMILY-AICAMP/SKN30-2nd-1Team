-- Post-load DB schema reference for TubeEottae EDA
-- Base collation: utf8mb4_unicode_ci
-- channel_info_table.youtube_channel_id must be indexed before FK creation.

-- Run once if the index does not already exist.
-- ALTER TABLE channel_info_table ADD INDEX idx_channel_info_youtube_channel_id (youtube_channel_id);

CREATE TABLE IF NOT EXISTS active_viewer_score_table (
    channel_id VARCHAR(64) NOT NULL,
    title VARCHAR(255),
    subscriber_count BIGINT UNSIGNED,
    avg_view_count DOUBLE,
    view_per_sub DOUBLE,
    cluster TINYINT,
    cluster_name VARCHAR(50),
    active_viewer_score DECIMAL(10,6),
    PRIMARY KEY (channel_id),
    CONSTRAINT fk_active_viewer_channel
        FOREIGN KEY (channel_id) REFERENCES channel_info_table(youtube_channel_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sensitive_keyword_score_table (
    channel_id VARCHAR(64) NOT NULL,
    channel_title VARCHAR(255),
    sensitive_score DECIMAL(10,6),
    n_sensitive_videos INT UNSIGNED,
    sensitive_video_ratio DECIMAL(10,6),
    cat_politics INT UNSIGNED,
    cat_hate INT UNSIGNED,
    cat_aggro INT UNSIGNED,
    cat_adult_illegal INT UNSIGNED,
    PRIMARY KEY (channel_id),
    CONSTRAINT fk_sensitive_keyword_channel
        FOREIGN KEY (channel_id) REFERENCES channel_info_table(youtube_channel_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS upload_regularity_score_table (
    channel_id VARCHAR(64) NOT NULL,
    channel_title VARCHAR(255),
    regularity_score DECIMAL(10,6),
    mean_interval_days DOUBLE,
    std_interval_days DOUBLE,
    max_gap_days DOUBLE,
    cv DOUBLE,
    outlier_ratio DECIMAL(10,6),
    gap_ratio DECIMAL(10,6),
    PRIMARY KEY (channel_id),
    CONSTRAINT fk_upload_regularity_channel
        FOREIGN KEY (channel_id) REFERENCES channel_info_table(youtube_channel_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS channel_prediction_table (
    channel_id VARCHAR(64) NOT NULL,
    title VARCHAR(255),
    churn_actual_label TINYINT,
    churn_prob_lr DECIMAL(10,6),
    churn_prob_rf DECIMAL(10,6),
    churn_prob_xgb DECIMAL(10,6),
    churn_prob DECIMAL(10,6),
    stagnation_actual_label TINYINT,
    stagnation_prob_lr DECIMAL(10,6),
    stagnation_prob_rf DECIMAL(10,6),
    stagnation_prob_xgb DECIMAL(10,6),
    stagnation_prob DECIMAL(10,6),
    volatility_actual_label TINYINT,
    volatility_prob_lr DECIMAL(10,6),
    volatility_prob_rf DECIMAL(10,6),
    volatility_prob_xgb DECIMAL(10,6),
    volatility_prob DECIMAL(10,6),
    has_churn TINYINT DEFAULT 0,
    has_stagnation TINYINT DEFAULT 0,
    has_volatility TINYINT DEFAULT 0,
    PRIMARY KEY (channel_id),
    CONSTRAINT fk_channel_prediction_channel
        FOREIGN KEY (channel_id) REFERENCES channel_info_table(youtube_channel_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS video_info_table (
    video_id VARCHAR(32) NOT NULL,
    channel_id VARCHAR(64) NOT NULL,
    channel_title VARCHAR(255),
    video_title TEXT,
    published_at DATETIME,
    duration_sec DOUBLE,
    is_shorts TINYINT,
    view_count BIGINT UNSIGNED,
    like_count BIGINT UNSIGNED,
    comment_count BIGINT UNSIGNED,
    source_file VARCHAR(255),
    channel_created_at DATETIME,
    country VARCHAR(8),
    subscriber_count BIGINT UNSIGNED,
    channel_total_views BIGINT UNSIGNED,
    total_video_count BIGINT UNSIGNED,
    PRIMARY KEY (video_id),
    INDEX idx_video_info_channel_id (channel_id),
    CONSTRAINT fk_video_info_channel
        FOREIGN KEY (channel_id) REFERENCES channel_info_table(youtube_channel_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
