# Reliability: kuch toot jaye to kya hota hai

| Kya toota | System kya karta hai | Kis din |
|---|---|---|
| Kharab/corrupt event | Reject hota hai, rejected_events mein save, dashboard pe dikhta hai | Day 35-37 |
| Postgres down | Consumer crash nahi hota | Day 38 |
| Kafka down | 2 sec timeout + retry; producer events memory mein rakhta hai | Day 39 |
| Consumer beech mein crash | Commit save ke baad hota hai, event kabhi khota nahi | Day 40 |
| Same event dobara aaye | Pehle se save hai to skip, Postgres mein dobara nahi jaata | Day 41 |

**Crash test (Day 42):** 7 events bheje, event #3 save ke baad crash karwaya.
BEFORE: 673 rows; restart ke baad AFTER: 680 rows. Lost: 0, Duplicates: 0.

Do repeat rounds bhi PASS hue:

| Crash point | BEFORE | SENT | AFTER | Result |
|---|---:|---:|---:|---|
| Event #1 | 680 | 7 | 687 | PASS |
| Event #5 | 687 | 7 | 694 | PASS |

Har replayed event `[SKIP]` hua; teeno rounds ke baad Kafka lag 0 tha.