# modules/encrypted_data.py
import base64
import logging
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

key = b'Ks9dNp3R7a2TqBhE5WjX6Zy8cVfUgHm4'

# Set the encrypted text directly
encrypted_creator_info = "1/d7iUIYnAtlUfsz8mdibg==:1MlIWbZaBjsx0Gbt72rQc0NLckKJWSiXmrpU4cB9Tw/cQaFcpOA0FGecr+yAELfnZgUviiIFGkb+2i/5DeGuTqYvrFAwgt9S1qYV81IK9VcMJsXmRO5bzf+7WGMow6J51N0EOko+EWXoCHn9154LGq571GFs7XZFW5rsWYLdB/qUXT37rg7gDDaLr1t3NlsayitNFgV7mbXIcuITbVohaK3pwNQkOh+hjf/vdfeDmMVCdeJQBbsE1iY8XLbWAqa1pJLvNdxs5VpYi/UTui8NBIsomij6E/i2HPaQXAkcLib2N2wRyg7k+cwxDcgpTEJsyJGKMI5tmxlBnA1UhLxd1Bnzkwnx0spgYCnLuFCntgHfl4BZjRxPs6Espt5LpT44e/uwMlkGThalRRoai3UJR3qJxkOHrTy1VP8VhPEHjjOY4ogZzqv8MpiiQXqXK3Y/bOKrjgU2cac4tkucQILcB4FAsdEyLSpPYWkOwG/MvS8ZWN3c1xXjGGxlTxyFWaTY+Bd7IC0wafLvOXrIrvCv1wngb2MWkQZ5Xxkr4IUx4Ec="

def encrypt(data):
    cipher = AES.new(key, AES.MODE_CBC)
    ciphertext = cipher.encrypt(pad(data.encode(), AES.block_size))
    iv = base64.b64encode(cipher.iv).decode('utf-8')
    encrypted_data = base64.b64encode(ciphertext).decode('utf-8')
    return f'{iv}:{encrypted_data}'

def decrypt(encrypted_data):
    try:
        iv, ciphertext = encrypted_data.split(':', 1)
        iv = base64.b64decode(iv)
        ciphertext = base64.b64decode(ciphertext)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted_data = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return decrypted_data.decode('utf-8')
    except ValueError as e:
        logger.error(f"Error during decryption: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during decryption: {e}")
        return None
