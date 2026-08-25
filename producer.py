import json
from kafka import KafkaProducer

# 1. Kafka se connection set up kar krenge abb
try:
    producer = KafkaProducer(
        bootstrap_servers=['localhost:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
except Exception as e:
    print(f"Kafka connection setup failed: {e}")
    producer = None

# 2. Ye function  main.py se call karunga
def send_error_to_kafka(error_data: dict):
    if not producer:
        print("Kafka producer initialized nahi hai.")
        return False
        
    try:
        # Message ko 'errors-topic' mein push kar raha hu
        producer.send('errors-topic', error_data)
        producer.flush()  # Ensures data actually leaves the memory buffer
        return True
    except Exception as e:
        print(f"Kafka publish failed: {e}")
        return False