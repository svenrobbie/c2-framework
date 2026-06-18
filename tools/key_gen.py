#!/usr/bin/env python3
import os

from Crypto.PublicKey import RSA
from Crypto.PublicKey import ECC

OUT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    print("=== Key Generator ===\n")

    print("[*] Generating RSA-2048 key pair...")
    key = RSA.generate(2048)
    private_key = key.export_key()
    public_key = key.public_key().export_key()

    rsa_priv_path = os.path.join(OUT_DIR, "prive_RSA.pem")
    rsa_pub_path = os.path.join(OUT_DIR, "publiek_RSA.pem")

    with open(rsa_priv_path, "wb") as f:
        f.write(private_key)
    print(f"    Private: {rsa_priv_path}")

    with open(rsa_pub_path, "wb") as f:
        f.write(public_key)
    print(f"    Public:  {rsa_pub_path}")

    print("\n=== Public key for embedding ===")
    print(public_key.decode())
    print("=== (copy above into agents/ransomware_linux.py or agents/ransomware_windows.py PUBLIC_KEY_PEM) ===\n")

    print("[*] Generating ECC P-256 key pair...")
    ecc_key = ECC.generate(curve='P-256')

    ecc_priv_path = os.path.join(OUT_DIR, "privekey_ecc.pem")
    ecc_pub_path = os.path.join(OUT_DIR, "publiekkey_ecc.pem")

    with open(ecc_priv_path, 'wt') as f:
        f.write(ecc_key.export_key(format="PEM"))
    print(f"    Private: {ecc_priv_path}")

    with open(ecc_pub_path, 'wt') as f:
        f.write(ecc_key.public_key().export_key(format='PEM'))
    print(f"    Public:  {ecc_pub_path}")

    print("\n[+] Key generation complete.")


if __name__ == '__main__':
    main()
