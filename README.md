# Error Intelligence Platform

## Root cause heuristic (cross-service correlation)

`GET /incident-correlation` checks open anomaly incidents. If multiple
incidents started within five minutes, it reports the earliest one as the
probable root cause and the later incidents as affected, with their lag in
seconds. This is a heuristic, not AI: an earlier incident is not necessarily
the cause. Since the watcher checks every 10 seconds, `lag_seconds` can vary
by roughly 10-15 seconds.

Live switch test (Payment ON, then Order ON 20 seconds later):

```json
{
  "root_cause": {
    "service_name": "order-service",
    "started_at": "2026-11-05T09:14:06.969508",
    "top_error": "DatabaseConnectionError (86 errors, last 5 min)"
  },
  "affected": [
    {
      "service_name": "payment-service",
      "lag_seconds": 0,
      "top_error": "PaymentGatewayTimeout (124 errors, last 5 min)"
    }
  ]
}
```

In this run, the watcher opened both incidents in the same observation, so
their incident start times tied and the response could not recover the
20-second switch order. The endpoint reports observed incident order, not
causality or the time a failure switch was flipped.

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

## Day 56: Index the error timestamp

The `errors.occurred_at` index supports time-based queries against the real
errors table. It is declared in the SQLAlchemy model and ensured at backend
startup for existing databases. Creating an index adds work to writes, so
compare the consumer drain rate before and after the index with the same
10,000-event test.

To benchmark query speed independently of application data, run
[`perf/index_experiment.sql`](./perf/index_experiment.sql) against PostgreSQL.
It recreates only the synthetic `errors_big` table, with 500,000 rows spread
over the last seven days, and runs the same 15-minute aggregate query before
and after adding the timestamp index. Run each `EXPLAIN ANALYZE` query two or
three times and record the smallest `Execution Time`; note the scan plan too.
The planner may show `Bitmap Index Scan` rather than `Index Scan` when that is
the cheaper choice.

Before measuring the consumer, check which indexes already exist:

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'errors';
```

At the time of this run, `errors` had `errors_pkey`, `ix_errors_fingerprint`,
`ix_errors_id`, and `uq_kafka_partition_offset`; it did not yet have an index
on `occurred_at`.

If `ix_errors_occurred_at` is absent, capture the before-index drain rate
before applying the SQL below or restarting the backend with this change
(startup automatically ensures the index). Run `python load_test.py 10000 drain`
with the consumer stopped while the events are queued. Start the consumer when
prompted and record its events/sec. Then add the index:

```sql
CREATE INDEX IF NOT EXISTS ix_errors_occurred_at ON errors (occurred_at);
```

Repeat the same drain test with the same services and settings. If the index
already existed before the first run, there is no valid before/after comparison
to report. Check that `extra/duplicate` stays at 0. Once the synthetic query
results are recorded, remove only its benchmark table:

```sql
DROP TABLE errors_big;
```

| Test | Before index | After index |
|---|---|---|
| Query: errors from the last 15 minutes (500,000 synthetic rows) | 40.466 ms (Parallel Seq Scan) | 1.143 ms (Bitmap Index Scan; about 35.4x faster) |
| Consumer drain, 10,000 events | Not measured: 36,758 older Kafka events were already queued | Not measured yet |

The 500,000 rows are synthetic and used only to benchmark query speed. The
query timings are measured by PostgreSQL. The drain comparison could not be
isolated because the Kafka consumer group already had 36,758 older events
queued before the test. The test events were queued and the consumer was
restarted to resume processing; do not treat the resulting backlog drain as a
10,000-event benchmark.

## Day 57: Anomaly incidents

An `ANOMALY` event opens an incident for that service unless one is already
open; repeated anomaly events do not create duplicates. A `NORMAL` event
resolves the open incident and records `resolved_at`, while `WARNING` leaves
incident state unchanged. `GET /anomaly-incidents` lists the latest 50
incidents and accepts an optional `?status=OPEN` filter. Live stopwatch
measurements (spike-to-open and switch-off-to-resolved) have not been taken.

## Day 59: Chain fire drill

`chain_test.py` automates the spike-to-incident-to-resolved timing test. It
defaults to the `payment-service` simulator and its file-existence switch,
`fail_payment-service.flag`; switch files are created beside the script, where
`service_simulator.py` looks for them. Change `TARGET_SERVICE` in the script
before testing another service. The API defaults to `http://127.0.0.1:8000`;
set `API_URL` to use another backend address.

Start PostgreSQL, Kafka, the backend, consumer, service simulators, and anomaly
watcher. Let the services build their baseline before the test, and resolve or
clear any old open anomaly incident for the target service. Then run:

```text
python chain_test.py
```

Each round turns the switch on until the target incident opens, holds the
failure for 30 seconds, turns it off, and waits for that incident to resolve.
The defaults are three rounds, a 60-second cooldown, and a 180-second timeout
per wait. Change the constants at the top of the script for a dry run or a
different test duration. The switch is turned off when the script exits.

Results are appended to `chain_test_results.csv` beside the script, including a
status for passed, failed, skipped, and API-error rounds. Detection and
recovery values are in whole seconds; summary output reports average, minimum,
and maximum. Live timings have not been measured yet:

| Round | Detection (spike ON to incident OPEN) | Recovery (spike OFF to RESOLVED) |
|---|---:|---:|
| 1 | Not measured | Not measured |
| 2 | Not measured | Not measured |
| 3 | Not measured | Not measured |
| Average | Not measured | Not measured |

## Day 60: Robust baseline (median and MAD)

The baseline now uses the median and median absolute deviation (MAD), with a
minimum sigma to avoid division by zero. This reduces baseline poisoning when
spike minutes are included in the lookback window. The existing `mean` and
`std_dev` response fields are retained for compatibility; their values now
represent the median and robust sigma. Both `/metrics/baseline` and anomaly
scoring use the same helper in `robust_stats.py`.

Run `python poison_lab.py` to compare the mean/std-dev and median/MAD baselines
using repeated spikes. This verifies the robust-statistics example without
requiring the live services.

Live run on 2026-11-03: the target had a robust baseline of `0.00` and sigma
`1.00` before the chain test and the same values afterward. Historical
pre-change baseline readings and Day 59 chain timings were not recorded:

| Baseline (target service) | mean / median | std_dev / sigma |
|---|---:|---:|
| Before spike (old baseline) | Not measured | Not measured |
| After one spike (old baseline) | Not measured | Not measured |
| Before and after spike (robust baseline) | 0.00 | 1.00 |

| Chain test (3 rounds) | Detection | Recovery |
|---|---:|---:|
| Day 59 (old baseline) | Not measured | Not measured |
| Day 60 (robust baseline) | Round 1: 42 s; rounds 2-3 skipped | Round 1: >180 s; rounds 2-3 skipped |

The Day 60 chain test did not pass: the first round opened an incident but did
not resolve within the 180-second timeout, so the remaining rounds were
skipped because the incident stayed open. A first attempt made before Redis
was started failed detection in all three rounds; those failures are not
included in the Day 60 timing above.

## Day 61: Top error on anomaly incidents

When an anomaly opens an incident, the backend finds the most frequent
`error_type` among that service's errors in the five-minute window ending at
the service's newest `occurred_at` value. The resulting text is stored in
`anomaly_incidents.top_error` and returned by `GET /anomaly-incidents`; it
remains on the incident after resolution. The dashboard shows it in the
“Kya toota” column. Incidents created before this change display `-`.

The backend startup adds the nullable column to existing PostgreSQL databases
with `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`; `create_all` alone does not
alter an existing table. To check the aggregate manually, substitute a service
name that exists in `errors`:

```sql
SELECT error_type, COUNT(*) AS n
FROM errors
WHERE service_name = 'payment'
  AND occurred_at >= (
        SELECT MAX(occurred_at) FROM errors WHERE service_name = 'payment'
      ) - INTERVAL '5 minutes'
GROUP BY error_type
ORDER BY n DESC
LIMIT 1;
```

### Demo flow

1. Start PostgreSQL, Kafka, Redis, the backend, consumer, the service
   simulators, anomaly watcher, and frontend.
2. Let the services collect baseline data, then run `python chain_test.py` with
   `ROUNDS = 1`.
3. Confirm the incident changes from OPEN to RESOLVED after the spike is
   switched off.
4. Anomaly incident OPEN hota hai; ticket mein service, status aur sabse
   zyada aane wala error (top error) likha hota hai.

The live API check on `payment-service` returned
`PaymentGatewayTimeout (136 errors, last 5 min)` and retained it after
resolution. The one-round real spike test did not detect an incident within
its 180-second timeout; the direct anomaly-event check verified the ticket
field and its persistence across resolution. The dashboard capture is
[`docs/anomaly-incident-open.png`](./docs/anomaly-incident-open.png).
