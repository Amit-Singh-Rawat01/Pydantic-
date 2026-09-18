# Day 35: Kafka Malformed Event Protection

## Goal

Kafka se aane wale ek corrupt ya invalid error event ko reject karke skip karna hai. Consumer crash nahi karega aur next valid event process hota rahega.

## Kya change hua

1. `schemas.py` mein `Severity` enum add hua:
   - `LOW`
   - `MEDIUM`
   - `HIGH`
   - `CRITICAL`
2. `ErrorEventSchema` required fields validate karta hai:
   - `service_name`
   - `error_type`
   - `message`
   - `severity`
   - optional `stack_trace`
   - optional input `occurred_at`, jiska default consumer boundary par UTC timestamp hai
3. `consumer.py` ab Kafka value ko raw bytes ke roop mein receive karta hai.
4. JSON decoding aur Pydantic validation consumer loop ke `try` block ke andar hoti hai.
5. Invalid JSON, invalid UTF-8, non-object JSON, missing fields, aur invalid severity ke liye log format hai:

```text
[REJECTED] Invalid event skipped. Reason: ...
```

6. Valid event ke liye existing fingerprint, database, incident, aur Redis counter flow unchanged hai.

## Local verification

Run the focused tests:

```powershell
python -m unittest test_event_validation.py
```

Expected result:

```text
Ran 5 tests ...
OK
```

Compile the changed files:

```powershell
python -m py_compile schemas.py consumer.py test_event_validation.py
```

## Manual Kafka verification

Kafka aur services start karo:

```powershell
docker compose up -d
```

Consumer logs dekho:

```powershell
docker compose logs -f consumer
```

Ek invalid event publish karo, jaise invalid severity ya missing service name. Example payload:

```json
{"error_type":"TimeoutError","message":"bad event","severity":"RANDOM_TEXT"}
```

Expected: consumer crash nahi karega aur `[REJECTED]` log dikhega.

Phir valid event publish karo:

```json
{"service_name":"payment-service","error_type":"TimeoutError","message":"provider timed out","severity":"HIGH"}
```

Expected: event database mein save hoga, incident processing chalegi, aur Redis counters update honge.

## Git wrap-up

```powershell
git diff --check
git add schemas.py consumer.py test_event_validation.py DAY35_MALFORMED_EVENTS.md
git commit -m "Add validation for malformed Kafka events in consumer"
git push
```
