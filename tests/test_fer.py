from config import config
from clients.fer_client import fer_client
import time

def test_fer_client():
    try:
        fer_client.send('IdentifyPatientByPhoneRequest', {'session_id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'phone': '+7(919)9340710'})    
    except Exception as e:
       print(f"Ошибка FER: {e}")
       return False

if __name__ == "__main__":
    test_fer_client()