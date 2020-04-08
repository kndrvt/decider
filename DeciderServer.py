#!/usr/bin/env python

# Quagga
from TelnetQuagga import TelnetQuagga

# Scapy
from scapy.all import *

# System
from signal import signal, SIGINT
from time import clock, sleep
from json import dumps
from requests import get
import os


class DeciderServer:

    def __init__(self, IP, telnetquagga, faasIP, faasPort, clientDeciders, maxrtt=5000, maxhop=64, bufsize=3,
                 duration=20):

        self.IP = IP
        self.telnetquagga = telnetquagga
        self.faasIP = faasIP
        self.faasPort = faasPort
        self.clientDeciders = clientDeciders
        self.maxrtt = maxrtt
        self.maxhop = maxhop
        self.rtt = defaultdict(list)
        self.rttav = defaultdict(float)
        self.hop = defaultdict(list)
        self.hopav = defaultdict(float)
        self.bufsize = bufsize
        self.faasMetrics = defaultdict(list)
        self.duration = duration  # seconds

    def start(self):

        while True:
            self.updateNetworkMetrics()
            self.updateFaasMetrics()
            self.updateTargetValues()
            sleep(2)

    def updateNetworkMetrics(self):

        for targetIP in self.clientDeciders:
            sum_rtt = 0
            sum_hop = 0
            n = 1
            for i in range(n):
                rtt, hop = self.ping(targetIP)
                sum_rtt += rtt
                sum_hop += hop

            if len(self.rtt[targetIP]) >= self.bufsize:
                self.rtt[targetIP].pop(0)
                self.hop[targetIP].pop(0)
            self.rtt[targetIP].append(sum_rtt / n)
            self.hop[targetIP].append(sum_hop / n)

            sum = 0
            for rtt in self.rtt[targetIP]:
                sum += rtt
            self.rttav[targetIP] = sum / len(self.rtt[targetIP])

            sum = 0
            for hop in self.hop[targetIP]:
                sum += hop
            self.hopav[targetIP] = sum / len(self.hop[targetIP])

            print(self.rttav[targetIP])
            print(self.hopav[targetIP])

    def updateFaasMetrics(self):

        self.faasMetrics.clear()
        URL = "http://" + self.faasIP + ":" + str(self.faasPort) + "/api/v1/"

        parameters = [
            # function invocation rate
            "query?query=rate(gateway_function_invocation_total{{code=\"200\"}}[{0}s])",
            # function replica count
            "query?query=gateway_service_count",
            # average function execution time
            "query?query=(rate(gateway_functions_seconds_sum[{0}s])\
           /rate(gateway_functions_seconds_count[{0}s]))"
        ]

        for parameter in parameters:
            response = get(URL + parameter.format(self.duration))
            # print(dumps(response.json(), indent=2, sort_keys=True))
            # print("================================================")
            if response.json()["status"] == "success":
                for result in response.json()['data']['result']:
                    value = result['value'][1]
                    if value != '0' and value != 'NaN':
                        self.faasMetrics[result['metric']['function_name']].append(float(value))
                    else:
                        self.faasMetrics[result['metric']['function_name']].append(float(0))
                        # self.faasMetrics.pop(result['metric']['function_name'], [])
            else:
                print("Response status differs from \'success\'")

        print(self.faasMetrics)

    def updateTargetValues(self):
        targetvalue = self.targetFunction('figlet', self.clientDeciders[0])
        print(targetvalue)

    def ping(self, targetIP):
        start = clock()
        ans, unans = sr(IP(dst=targetIP, ttl=64) / ICMP(), timeout=10)
        if ans:
            return 1000 * (clock() - start), 64 - ans[0][1][IP].ttl + 1
        else:
            return self.maxrtt, self.maxhop

    def targetFunction(self, function, decider):
        return self.rtt[decider][0] / 10 + \
               self.hop[decider][0] / 64 + \
               (self.faasMetrics[function])[0] + \
               1 / (self.faasMetrics[function])[1] + \
               100 * (self.faasMetrics[function])[2]


def signalHandler(signum, frame):
    print()
    print('=== Stopping Server decider ===')
    exit()


if __name__ == '__main__':
    print()
    print('=== Starting Server decider ===')
    signal(SIGINT, signalHandler)

    tq = TelnetQuagga(host="127.0.0.1", port=2605)
    faasIP = '10.0.9.1'
    faasPort = 9090
    deciderIP = '10.0.8.52'
    # clientDeciders = ['10.0.8.51']
    clientDeciders = ['10.0.9.1']

    deciderServer = DeciderServer(deciderIP, tq, faasIP, faasPort, clientDeciders)
    deciderServer.start()
