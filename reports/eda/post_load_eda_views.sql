-- Post-load EDA views
-- These views assume all existing and additional tables have been loaded.
-- Adjust category/band join keys if the physical DB uses different column names.

CREATE OR REPLACE VIEW v_channel_score_eda AS
SELECT
    ci.channel_identifier,
    ci.youtube_channel_id,
    ci.channel_name,
    av.active_viewer_score,
    av.view_per_sub,
    av.cluster_name,
    sk.sensitive_score,
    sk.n_sensitive_videos,
    sk.sensitive_video_ratio,
    ur.regularity_score,
    ur.mean_interval_days,
    ur.max_gap_days,
    cp.churn_prob,
    cp.stagnation_prob,
    cp.volatility_prob,
    cp.has_churn,
    cp.has_stagnation,
    cp.has_volatility
FROM channel_info_table ci
LEFT JOIN active_viewer_score_table av
    ON av.channel_id = ci.youtube_channel_id
LEFT JOIN sensitive_keyword_score_table sk
    ON sk.channel_id = ci.youtube_channel_id
LEFT JOIN upload_regularity_score_table ur
    ON ur.channel_id = ci.youtube_channel_id
LEFT JOIN channel_prediction_table cp
    ON cp.channel_id = ci.youtube_channel_id;

CREATE OR REPLACE VIEW v_video_activity_eda AS
SELECT
    ci.channel_identifier,
    ci.youtube_channel_id,
    vi.video_id,
    vi.video_title,
    vi.published_at,
    vi.duration_sec,
    vi.is_shorts,
    vi.view_count,
    vi.like_count,
    vi.comment_count
FROM video_info_table vi
JOIN channel_info_table ci
    ON vi.channel_id = ci.youtube_channel_id;

-- comments_table is intentionally kept independent from video_info_table
-- because the collected comment video_id may differ from video_info_table.video_id.
