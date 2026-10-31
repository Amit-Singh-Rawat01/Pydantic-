-- Day 56: compare the same 15-minute query before and after adding an index.
-- This table is synthetic and separate from the application's errors table.
-- Re-running the experiment replaces only this benchmark table.
DROP TABLE IF EXISTS errors_big;

CREATE TABLE errors_big AS
SELECT
    (ARRAY['payment', 'auth', 'order'])[1 + floor(random() * 3)::int]
        AS service_name,
    NOW() - random() * INTERVAL '7 days' AS occurred_at
FROM generate_series(1, 500000);

ANALYZE errors_big;

-- Baseline: record the plan name and Execution Time (ms).
EXPLAIN ANALYZE
SELECT service_name, COUNT(*)
FROM errors_big
WHERE occurred_at >= NOW() - INTERVAL '15 minutes'
GROUP BY service_name;

EXPLAIN ANALYZE
SELECT service_name, COUNT(*)
FROM errors_big
WHERE occurred_at >= NOW() - INTERVAL '15 minutes'
GROUP BY service_name;

EXPLAIN ANALYZE
SELECT service_name, COUNT(*)
FROM errors_big
WHERE occurred_at >= NOW() - INTERVAL '15 minutes'
GROUP BY service_name;

-- Add the timestamp index, then run the exact same query again.
CREATE INDEX ix_errors_big_occurred_at ON errors_big (occurred_at);
ANALYZE errors_big;

EXPLAIN ANALYZE
SELECT service_name, COUNT(*)
FROM errors_big
WHERE occurred_at >= NOW() - INTERVAL '15 minutes'
GROUP BY service_name;

EXPLAIN ANALYZE
SELECT service_name, COUNT(*)
FROM errors_big
WHERE occurred_at >= NOW() - INTERVAL '15 minutes'
GROUP BY service_name;

EXPLAIN ANALYZE
SELECT service_name, COUNT(*)
FROM errors_big
WHERE occurred_at >= NOW() - INTERVAL '15 minutes'
GROUP BY service_name;

-- Leave errors_big available until the result has been recorded.
-- Clean it up with: DROP TABLE errors_big;
