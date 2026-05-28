import json
import asyncio
import threading
from src.utils.htmltem import getHtml
try:
    from kafka import KafkaProducer, KafkaConsumer
except ModuleNotFoundError as e:
    KafkaProducer = None
    KafkaConsumer = None
    kafkaImportError = e
else:
    kafkaImportError = None
try:
    from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
except ModuleNotFoundError as e:
    FastMail = None
    MessageSchema = None
    ConnectionConfig = None
    MessageType = None
    mailImportError = e
else:
    mailImportError = None

from src.utils.settings import settings

# Kafka Producer 설정
kafkaProducer = None
if KafkaProducer is not None:
  kafkaProducer = KafkaProducer(
    bootstrap_servers=settings.kafka_server,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
  )

# mail config 설정
fastMail = None
if ConnectionConfig is not None and FastMail is not None:
  mailConf = ConnectionConfig(
    MAIL_USERNAME = settings.mail_username,
    MAIL_PASSWORD = settings.mail_password,
    MAIL_FROM = settings.mail_from,
    MAIL_PORT = settings.mail_port,
    MAIL_SERVER = settings.mail_server,
    MAIL_FROM_NAME = settings.mail_from_name,
    MAIL_STARTTLS = settings.mail_starttls,
    MAIL_SSL_TLS = settings.mail_ssl_tls,
    USE_CREDENTIALS = settings.use_credentials,
    VALIDATE_CERTS = settings.validate_certs
  )
  fastMail = FastMail(mailConf)

# Producer 함수 
def sendToKafka(data):
    """API 서버에서 메시지를 보낼 때 사용"""
    if kafkaProducer is None:
        print(f"Kafka is unavailable; message was not sent. importError={kafkaImportError}")
        return False
    kafkaProducer.send(settings.kafka_topic, data)
    kafkaProducer.flush()
    return True

# Consumer 이메일 발송 함수
# html1: 사내 직원 초대
# html2: 컨설턴트 초대 (신규: type 2, 기존: type 3)
# html3: 임시 비밀번호 발송
# html4: 협력사 초대 메일 발송

async def handleEmailJob(data):
    """
    이메일 발송 핸들러
    data 예시: 
    {"type": 1, "email": "user@example.com", "companyName": "회사명"}
    {"type": 2, "email": "user@example.com", "companyName": "회사명"}
    {"type": 3, "email": "user@example.com", "companyName": "회사명"}
    {"type": 4, "email": "user@example.com", "tempPwd": "임시비밀번호"} 
    """

    # 1. 타입에 따른 제목 및 본문 설정
    if fastMail is None:
        print(f"FastAPI mail is unavailable; email was not sent. importError={mailImportError}")
        return False

    subject, body, email = getHtml(data)
    if subject:
        message = MessageSchema(
            subject=subject,
            recipients=[email],
            body=body,
            subtype=MessageType.html
        )
        await fastMail.send_message(message)
    else:
        print(f"알 수 없는 이메일: {email}")

# Consumer 함수
def runEmailConsumer():
    """이메일 토픽 컨슈머 루프"""
    if KafkaConsumer is None:
        print(f"Kafka consumer is unavailable; email consumer was not started. importError={kafkaImportError}")
        return
    consumer = KafkaConsumer(
        settings.kafka_topic, 
        bootstrap_servers=settings.kafka_server,
        enable_auto_commit=True,
        value_deserializer=lambda v: json.loads(v.decode("utf-8"))
    )
    for message in consumer:
        asyncio.run(handleEmailJob(message.value))

def startConsumer():
    """컨슈머 시작 함수"""
    emailThread = threading.Thread(target=runEmailConsumer, daemon=True)
    emailThread.start()
