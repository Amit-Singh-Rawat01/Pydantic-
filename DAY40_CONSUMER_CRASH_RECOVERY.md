# Day 40: Consumer Crash Recovery Without Event Loss

## Goal

Kafka offsets ab automatic nahi, successful processing ke baad manually commit honge. Consumer processing ke beech crash ho jaye to last uncommitted event restart ke baad dobara milega. Isse at-least-once delivery milti hai: event miss nahi hoga, lekin crash boundary par duplicate row possible hai.

## Kya change hua

1. `consumer.py` mein `enable_auto_commit=False` set hai. Long-running consumer ko iterator timeout nahi diya gaya, taaki group membership stable rahe.
2. Valid event ke database save, incident handling, aur Redis counter flow ke baad `consumer.commit()` hota hai.
3. Invalid event ka rejected record database mein save hone ke baad hi uska offset commit hota hai.
4. Database ya rejected-event write fail hone par exception re-raise hoti hai. Offset commit nahi hota, aur Docker consumer ko restart karta hai.

## Normal verification

Services start karo:

```powershell
docker compose up -d
```

Consumer logs dekho:

```powershell
docker compose logs -f consumer
```

Expected successful event logs:

```text
Saved to DB successfully.
Redis counters updated.
Kafka offset committed after successful processing.
```

## Crash verification

1. Simulator se events continuously publish karo.
2. Consumer logs mein processing dekhte hue `docker compose kill consumer` chalao.
3. Consumer restart karo: `docker compose up -d consumer`.
4. PostgreSQL mein `errors` rows aur simulator ke sent events compare karo.

Crash ke waqt process ho raha event dobara save ho sakta hai. Ye expected duplicate hai; missing event nahi hona chahiye.

## Focused checks

```powershell
python -m unittest test_event_validation.py test_consumer_offsets.py
python -m py_compile consumer.py test_consumer_offsets.py
git diff --check
```

## Git wrap-up

```powershell
git add consumer.py test_consumer_offsets.py DAY40_CONSUMER_CRASH_RECOVERY.md
git commit -m "Day 40: manual offset commit to prevent event loss on consumer crash"
```