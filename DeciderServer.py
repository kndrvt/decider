#!/usr/bin/env python

# Quagga
from TelnetQuagga import TelnetQuagga

# Scapy
from scapy.all import *

def updateNetworkMetrics(tq, deciderIP, targetIP):
    pass

def updateServerlessMetrics(tq, deciderIP, faasIP):
    pass

def networkMetrics(targetIP):
    start = clock()
    ans, unans = sr(IP(dst=targetIP, ttl=64) / ICMP())
    return 1000 * (clock() - start), ans[0][1][IP].ttl


def signalHandler(signum, frame):
    print()
    print('=== Stopping Server decider ===')
    exit()


if __name__ == '__main__':

    print()
    print('=== Starting Server decider ===')
    signal(SIGINT, signalHandler)

    tq = TelnetQuagga(host="127.0.0.1", port=2605)
    faasIP = '10.0.6.1'
    deciderIP = '10.0.8.52'
    clientDeciders = ['10.0.8.51']

    while True:
        for targetIP in clientDeciders:
            updateNetworkMetrics(tq, deciderIP, targetIP)
            updateServerlessMetrics(tq, deciderIP, faasIP)


