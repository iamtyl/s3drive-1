import pgpy
from pgpy.constants import PubKeyAlgorithm
import os

def encrypt_symmetric(data, passphrase):
    """Encrypts data using a symmetric passphrase."""
    # In PGPy, symmetric encryption is done directly on the message
    message = pgpy.PGPMessage.new(data)
    encrypted_data = message.encrypt(passphrase)
    return encrypted_data.serialize()

def encrypt_asymmetric(data, public_key_text):
    """Encrypts data using a PGP public key."""
    key, _ = pgpy.PGPKey.from_blob(public_key_text)
    message = pgpy.PGPMessage.new(data)
    encrypted_data = message.encrypt(key)
    return encrypted_data.serialize()

def encrypt_file(file_path, passphrase=None, public_key=None):
    """
    Encrypts a file and returns the encrypted content.
    If passphrase is provided, uses symmetric. 
    If public_key is provided, uses asymmetric.
    """
    with open(file_path, 'rb') as f:
        data = f.read()
    
    if public_key:
        return encrypt_asymmetric(data, public_key)
    elif passphrase:
        return encrypt_symmetric(data, passphrase)
    else:
        raise ValueError("Either a passphrase or a public key must be provided.")
