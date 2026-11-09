from redis_client import redis_client as r


total = 0
per_service = {}

for key in r.scan_iter("errors:*"):
    _, service, _ = key.split(":", 2)
    count = int(r.get(key))
    per_service[service] = per_service.get(service, 0) + count
    total += count

print("service-wise:", per_service)
print("Redis total :", total)
