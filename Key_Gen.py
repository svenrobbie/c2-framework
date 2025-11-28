from Crypto.PublicKey import RSA
from Crypto.PublicKey import ECC

#Generate Keys
key = RSA.generate(2048)
prive_key = key.export_key()
public_key = key.public_key().export_key()

#Export functie
with open("prive_RSA.pem", "wb") as x:
    x.write(prive_key)

with open("publiek_RSA.pem", "wb") as x:
    x.write(public_key)

#Generate ECC keys.
key = ECC.generate(curve='P-256')
x = open('privekey_ecc.pem', 'wt')
x.write(key.export_key(format="PEM"))
x.close()

x = open('publiekkey_ecc.pem', "wt")
x.write(key.public_key().export_key(format='PEM'))
x.close()