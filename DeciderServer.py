#!/usr/bin/env python

# Quagga
from TelnetQuagga import TelnetQuagga

# Scapy
from scapy.all import *

# System
from signal import signal, SIGINT
from time import clock, sleep


class DeciderServer:

    def __init__(self, IP, telnetquagga, faasIP, clientDeciders, maxrtt=5000, maxhop=64, bufsize=3):

        self.IP = IP
        self.telnetquagga = telnetquagga
        self.faasIP = faasIP
        self.clientDeciders = clientDeciders
        self.maxrtt = maxrtt
        self.maxhop = maxhop
        self.rtt = defaultdict(list)
        self.hop = defaultdict(list)
        self.bufsize = bufsize

    def start(self):

        while True:
            self.updateNetworkMetrics()
            self.updateServerlessMetrics()
            self.updateTargetValue()
            sleep(2)

    def updateNetworkMetrics(self):

        for targetIP in self.clientDeciders:
            sum_rtt = 0
            sum_ttl = 0
            n = 1
            for i in range(n):
                rtt, ttl = self.ping(targetIP)
                sum_rtt += rtt
                sum_ttl += ttl

            if len(self.rtt[targetIP]) >= self.bufsize:
                self.rtt[targetIP].pop(0)
                self.hop[targetIP].pop(0)
            self.rtt[targetIP].append(sum_rtt / n)
            self.hop[targetIP].append(64 - sum_ttl / n)

            print(self.rtt[targetIP])
            print(self.hop[targetIP])

    def updateServerlessMetrics(self):
        pass

    def updateTargetValue(self):
        pass

    def ping(self, targetIP):
        start = clock()
        ans, unans = sr(IP(dst=targetIP, ttl=64) / ICMP(), timeout=5)
        if ans:
            return 1000 * (clock() - start), ans[0][1][IP].ttl
        else:
            return self.maxrtt, self.maxhop


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
    # clientDeciders = ['10.0.8.51']
    clientDeciders = ['8.8.8.8']

    deciderServer = DeciderServer(deciderIP, tq, faasIP, clientDeciders)
    deciderServer.start()
