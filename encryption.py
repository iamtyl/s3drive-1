from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

def encrypt_symmetric(data, passphrase):
    """Encrypts data using a symmetric passphrase (AES-GCM)."""
    # Derive a 32-byte key from the passphrase
    # For simplicity in this tool, we'll use a basic hash for the key
    import hashlib
    key = hashlib.sha256(passphrase.encode()).digest()
    
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, data, None)
    
    # Return nonce + ciphertext
    return nonce + ciphertext

def encrypt_asymmetric(data, public_key_text):
    """
    Encrypts data using a hybrid RSA approach.
    1. Generate random AES-GCM key.
    2. Encrypt data with AES-GCM.
    3. Encrypt AES key with RSA Public Key.
    4. Bundle: [Len of Encrypted Key (4 bytes)] + [Encrypted Key] + [Nonce (12 bytes)] + [Ciphertext]
    """
    # Load the RSA public key from PEM format
    public_key = serialization.load_pem_public_key(public_key_text.encode())
    
    # 1. Generate a random 32-byte symmetric key
    session_key = AESGCM.generate_key(bit_length=256)
    
    # 2. Encrypt the data with the session key
    aesgcm = AESGCM(session_key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, data, None)
    
    # 3. Encrypt the session key with the RSA Public Key
    encrypted_session_key = public_key.encrypt(
        session_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    
    # 4. Bundle everything
    # Length of the encrypted key is needed for decryption
    key_len = len(encrypted_session_key).to_bytes(4, byteorder='big')
    
    return key_len + encrypted_session_key + nonce + ciphertext

def encrypt_file(file_path, passphrase=None, public_key=None):
    """
    Encrypts a file and returns the encrypted content.
    """
    with open(file_path, 'rb') as f:
        data = f.read()
    
    if public_key:
        return encrypt_asymmetric(data, public_key)
    elif passphrase:
        return encrypt_symmetric(data, passphrase)
    else:
        raise ValueError("Either a passphrase or a public key must be provided.")
