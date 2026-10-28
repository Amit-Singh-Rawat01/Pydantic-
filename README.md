# Error Intelligence Platform

## Day 54: Pipeline load test

The load test sends events through `POST /errors` and waits for them to be
persisted by the Kafka consumer in PostgreSQL. Events use the `load-test`
service name, so they can be separated from normal simulator traffic.
`GET /metrics/total-errors` returns `{"total": ...}` with the current number
of rows in the errors table; its optional `service_name` filter lets the load
test count only its own events even if other producers are active.

Start PostgreSQL, Kafka, the consumer, and the API. Stop the service simulators
and anomaly watcher during a run so unrelated events do not affect the total
count. In another terminal, run:

```text
python load_test.py 100
python load_test.py 1000
python load_test.py 5000
python load_test.py 10000
```

Successful runs are recorded in `load_test_results.csv`. The 100-event smoke
run is intentionally excluded from the baseline because it encountered an
existing Kafka backlog. Results from the real runs:

| Label | Events | Sender events/sec | Pipeline events/sec | Result |
|---|---:|---:|---:|---|
| baseline | 1,000 | 75.7 | 24.4 | completed |
| baseline | 5,000 | N/A | N/A | timed out after 300 seconds |
| baseline | 10,000 | N/A | N/A | timed out after 300 seconds |

The completed run shows the consumer is the bottleneck: the pipeline ran at
24.4 events/sec versus 75.7 events/sec sent, with 27.9 seconds of additional
drain time. The 5,000- and 10,000-event runs did not fully drain before the
timeout, so they have no completed pipeline-throughput value.

After recording the baseline, remove only the test service's data from
PostgreSQL:

```sql
DELETE FROM errors WHERE service_name = 'load-test';
DELETE FROM incidents WHERE service_name = 'load-test';
DELETE FROM anomaly_events WHERE service_name = 'load-test';
```
