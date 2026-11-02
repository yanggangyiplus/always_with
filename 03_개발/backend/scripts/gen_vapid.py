"""Web Push용 VAPID 키 한 쌍을 만들어 환경변수 형식으로 출력한다. 비공개 키는 저장소에 올리지 않는다."""
import base64

from cryptography.hazmat.primitives import serialization as s
from py_vapid import Vapid

b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()  # noqa: E731
v = Vapid()
v.generate_keys()
print("VAPID_PRIVATE_KEY=" + b64(v.private_key.private_numbers().private_value.to_bytes(32, "big")))
print("VAPID_PUBLIC_KEY=" + b64(v.public_key.public_bytes(s.Encoding.X962, s.PublicFormat.UncompressedPoint)))
print("VAPID_SUBJECT=mailto:본인메일")
