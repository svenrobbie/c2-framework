RSA Randsomware

A lightweight pythonscript that recursively encrypts all files within a specified directory using RSA public-key encryption.

Features

🔐 RSA Public-Key Encryption
Uses a provided RSA public key to encrypt all files.
Only holders of the matching private key can decrypt.

📁 Recursive Directory Encryption
Automatically walks through all subdirectories and encrypts each file.

🛡️ Safe Encryption Process

Automatically skips already-encrypted files to avoid corruption.

How It Works

The tool loads an RSA public key from memory. (Hardcoded)

All files in the target directory are scanned recursively.

For each file:

File contents are encrypted.

The file content is encrypted using the RSA public key.

An output file (e.g., <filename>.<extension>) is created & overwrites the old file.

An README is created that will tell the user where to wire money for the decryption key.
