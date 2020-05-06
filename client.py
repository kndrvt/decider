#!/usr/bin/python3

import os
import sys
import signal
import numpy as np
import time


def signalHandler(signum, frame):
    print()
    print('=== Loading stopping ===')
    exit()


if __name__ == '__main__':

    if len(sys.argv) < 2:
        print('Usage: sudo python3 client.py <IP address>')
        exit()

    input = "default"
    if len(sys.argv) > 2:
        input = " ".join(sys.argv[2:])

    print()
    print('=== Loading starting ===')
    signal.signal(signal.SIGINT, signalHandler)
    np.random.seed()

    while True:
        os.system("echo \"" + input + "\" | faas-cli -g " + sys.argv[1] + ":8080 invoke figlet")
        time.sleep(0.01 * np.random.poisson(lam=100))
