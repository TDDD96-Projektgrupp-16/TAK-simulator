import socket

import logging
logger = logging.getLogger(__name__)

def host_ip() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect(("8.8.8.8", 80))
        addr, port = sock.getsockname()
    return addr
