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

## Day 55: Batch Kafka offset commits

The consumer now commits offsets after every 100 successfully handled messages
or when the 5-second interval is reached while processing messages. Both saved
events and persisted rejected events count toward the batch. PostgreSQL is still
committed before the Kafka offset, and the Day 41 Kafka partition/offset
uniqueness check makes redelivered events safe after a crash.

Use drain mode to queue the events before starting the consumer. Keep the
backend, PostgreSQL, and Kafka running; stop the consumer, simulators, and
anomaly watcher. For the per-event baseline use the pre-Day-55 consumer, or set
`BatchCommitter(consumer, every=1)` to emulate its commit frequency. Then start
the consumer when prompted. Set `LABEL` and the committer batch size for each
run:

```text
python load_test.py 10000 drain
```

Run once each with labels `commit-1`, `commit-100` (batch size 100), and
`commit-500` (batch size 500). For every run, wait for the output and check that
`extra/duplicate` is 0. The drain results are appended to
`load_test_results.csv`. Repeat the run with the label `chaos`, stopping and
restarting the consumer twice while it drains; all events should eventually
reach PostgreSQL and the extra count should remain 0.

| Label | Consumer events/sec |
|---|---:|
| commit-1 | Not measured |
| commit-100 | Not measured |
| commit-500 | Not measured |

These Day 55 measurements and the chaos run have not yet been run against the
live services. Batch commits reduce offset-commit requests, but a crash can
redeliver up to the uncommitted batch; the database uniqueness check prevents
those redeliveries from becoming duplicate error rows.
