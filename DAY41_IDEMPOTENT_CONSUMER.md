# Day 41: Kafka Partition/Offset Se Idempotent Writes

## Goal

Kafka at-least-once delivery se event miss nahi hota, lekin crash ke baad wahi message replay ho sakta hai. `kafka_partition` aur `kafka_offset` pair ko unique key bana kar `errors` mein duplicate row, incident processing, aur Redis counter increments roke jaate hain. Ye Day 26 fingerprint se alag hai: fingerprint similar errors ko group karta hai; Kafka coordinates ek exact message ko identify karte hain.

## Database migration

Existing Postgres database par ye SQL ek baar chalao:

```sql
ALTER TABLE errors ADD COLUMN kafka_partition INTEGER;
ALTER TABLE errors ADD COLUMN kafka_offset BIGINT;
ALTER TABLE errors ADD CONSTRAINT uq_kafka_partition_offset
    UNIQUE (kafka_partition, kafka_offset);
```

Purane rows ke dono naye columns `NULL` rahenge. Postgres unique constraint mein multiple `NULL` pairs allowed hain. SQLAlchemy model existing database ko alter nahi karta, isliye consumer restart karne se pehle migration chalao.

## Consumer behavior

1. Consumer insert mein message ka `partition` aur `offset` store karta hai.
2. `ON CONFLICT DO NOTHING` duplicate coordinate pair ko skip karta hai.
3. Sirf nayi row insert hone par incident detection aur Redis realtime counters chalte hain.
4. Successful handling ke baad hi Day 40 ki tarah Kafka offset manually commit hota hai. DB failure par offset commit nahi hota.

## Replay verification

Pehle migration apply karke services start karo:

```powershell
docker compose up -d
```

Duplicate replay test ke liye consumer ka `consumer.commit()` temporarily comment out karo. Consumer ko kuch messages process karne do, phir Ctrl+C se rok do. Count dekho:

```sql
SELECT COUNT(*) FROM errors;
```

`consumer.commit()` wapas enable karke consumer restart karo aur usi query ko dobara chalao. Count same rehna chahiye; replayed messages se errors, incidents, aur Redis counters dobara increment nahi hone chahiye. Test ke baad consumer ko original committed-offset behavior par hi chhodo.

Dashboard par Total Errors aur Errors-per-min ko replay ke baad achanak badhna nahi chahiye.

## Focused checks

```powershell
python -m unittest test_event_validation.py test_consumer_offsets.py
python -m py_compile consumer.py models.py test_consumer_offsets.py
git diff --check
```

## Git wrap-up

```powershell
git add consumer.py models.py test_consumer_offsets.py DAY41_IDEMPOTENT_CONSUMER.md
git commit -m "Day 41: idempotent consumer - dedup writes using Kafka partition+offset"
```