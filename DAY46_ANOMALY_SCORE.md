# Day 47: Z-score status classification

`GET /metrics/anomaly-score` reports a per-service score based on the most
recent complete minute and up to 30 complete preceding minutes. The `status`
is `NORMAL` below a z-score of 2, `WARNING` from 2 up to (but not including) 3,
and `ANOMALY` at 3 or above. If fewer than five minutes of history are
available since the service's first observed error, `z_score` is `null` and
`status` is `NO_DATA`.

Minutes without errors are counted as zero in the baseline. The current
complete minute is excluded from the baseline. A service appears after it has
at least one error in the queried window; services with no errors in that
window cannot be inferred from the errors table.

To exercise the endpoint, allow the services to produce normal errors for
several minutes, then query it. Enable the Payment failure switch briefly and
query again after the next complete minute. Disable the switch promptly,
because a sustained spike will eventually enter the rolling baseline.
