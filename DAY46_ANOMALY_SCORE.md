# Day 46: Z-score anomaly score

`GET /metrics/anomaly-score` reports a per-service score based on the most
recent complete minute and up to 30 complete preceding minutes. A score above
3 is reported as `ANOMALY`; a lower score is `NORMAL`. If fewer than five
minutes of history are available since the service's first observed error,
the response reports `NOT_ENOUGH_DATA`.

Minutes without errors are counted as zero in the baseline. The current
complete minute is excluded from the baseline. A service appears after it has
at least one error in the queried window; services with no errors in that
window cannot be inferred from the errors table.

To exercise the endpoint, allow the services to produce normal errors for
several minutes, then query it. Enable the Payment failure switch briefly and
query again after the next complete minute. Disable the switch promptly,
because a sustained spike will eventually enter the rolling baseline.
