from Crypto.PublicKey import RSA

#Generate Keys
key = RSA.generate(2048)
prive_key = key.export_key()
public_key = key.public_key().export_key()

#Export functie (NIET GEBRUIKEN, OVERWRITE ALLES)
with open("prive.pem", "wb") as x:
    x.write(prive_key)

with open("publiek.pem", "wb") as x:
    x.write(public_key)