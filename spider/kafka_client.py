import json
from kafka import KafkaProducer
from kafka.errors import kafka_errors
producer = KafkaProducer(
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    # bootstrap_servers=['192.168.10.136:9093', '192.168.10.136:9094', '192.168.10.136:9095', '192.168.10.136:9096', '192.168.10.136:9097'],
    bootstrap_servers=['139.159.247.16:9092',]
)

