# Day 45: Per-service error baseline

`GET /metrics/baseline?lookback_minutes=30` reports each observed service's
mean and population standard deviation of errors per minute. It looks back
30 minutes from five minutes before the current UTC minute, excluding recent
errors that may belong to an active spike. Minutes without errors are counted
as zero.

To verify against live data, run the PostgreSQL, Kafka, consumer, backend, and
service simulators in normal mode long enough to populate the requested
window. Compare the baseline mean with the per-minute counts from the same
window. A newly started service with no errors in that window will not appear
in the response.
