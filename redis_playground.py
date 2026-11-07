from redis_client import redis_client


count = redis_client.incr("test:counter")
redis_client.expire("test:counter", 60)

print("counter:", count)
print("time bacha (sec):", redis_client.ttl("test:counter"))
