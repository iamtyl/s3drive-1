
import pgpy
from pgpy.constants import PubKeyAlgorithm

# Generate a new RSA 4096-bit PGP key pair
print("Generating a new 4096-bit RSA PGP key pair... (this may take a minute) ✨")
key = pgpy.PGPKey.new(PubKeyAlgorithm.RSA, 4096)

# Set a basic user ID (required for PGP keys)
uid = pgpy.PGPUserID("S3Drive User <user@s3drive>")
key.add_user_id(uid)

# Save the Private Key (as ASCII armored text)
with open("private.asc", "w") as f:
    f.write(str(key))

# Save the Public Key (as ASCII armored text)
with open("public.asc", "w") as f:
    f.write(str(key.pubkey))

print("✅ PGP Keys generated successfully!")
print("Files created: private.asc, public.asc")
