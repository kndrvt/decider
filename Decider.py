#!/usr/bin/python3

# Scapy
from scapy.all import *
from scapy.layers.http import HTTP, HTTPResponse

# HTTP
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread, Lock
from requests import get, post
from json import loads, dumps

# System
from signal import signal, alarm, SIGINT, SIGALRM, SIGTERM
from time import sleep, time
from os import path, mkdir

# Statistics
import matplotlib.pyplot as plt
import numpy as np

# data
start_time = time()
time_line = []
times = []
# faas_metrics_names = ['Invocation rate', 'Replica count', 'Execution time']
faas_metrics_names = ['Частота, 1/с', 'Кол-во реплик', 'Время выполнения, с']
# network_metrics_names = ['RTT', 'Hops']
network_metrics_names = ['RTT, мс', 'Кол-во хопов']
serverless_hosts = ['10.0.1.1', '10.0.2.1', '10.0.3.1']
best_hosts = []
metrics_values = dict()
server_state = 'start'
kill_reg = True
rate = 1


class Decider(HTTPServer):

    def __init__(self, IP, Port, faasPort, regServerIP, regServerPort, pause=10, maxrtt=5000, maxhop=64, bufsize=1):
        HTTPServer.__init__(self, server_address=(IP, Port), RequestHandlerClass=HTTPRequestHandler)
        self.IP = IP
        self.Port = Port
        self.faasPort = faasPort
        self.lock = Lock()
        self.regServerIP = regServerIP
        self.regServerPort = regServerPort
        self.hosts = []
        self.pause = pause  # seconds
        self.maxrtt = maxrtt
        self.maxhop = maxhop
        self.rtt = defaultdict(list)
        self.rttav = defaultdict(float)
        self.hop = defaultdict(list)
        self.hopav = defaultdict(float)
        self.bufsize = bufsize
        self.faasMetrics = defaultdict(dict)
        self.faasMetricsNames = ['inv_rate', 'rep_count', 'exec_time']
        self.bestHosts = defaultdict(str)
        self.handler = None
        self.isRunning = False

    def start(self):
        self.isRunning = True
        self.handler = Thread(target=self.updateAll)
        self.handler.start()
        self.serve_forever()

    def finish(self):
        self.isRunning = False
        self.handler.join()
        self.server_close()

    def handle(self, data):
        http = HTTP(data)
        if http.name == 'HTTP 1':
            httpr = http.payload

            if httpr.name == 'HTTP Request':

                s = httpr.Path.decode('ascii')
                n = s.rindex("/")
                faasIP = self.decide(s[n + 1:])

                print()
                print("=== Redirection ===")
                print(httpr.summary(), " --> ", faasIP)

                if faasIP:
                    global response
                    if httpr.Method.decode('ascii') == 'POST':
                        response = post(url="http://" + faasIP + ':' + str(self.Port) + httpr.Path.decode('ascii'),
                                        data=httpr.payload.load.decode('ascii'))
                    elif http.Method.decode('ascii') == 'GET':
                        response = get(url="http://" + faasIP + ':' + str(self.Port) + httpr.Path.decode('ascii'),
                                       data=httpr.payload.load.decode('ascii'))
                    else:
                        print("Other request method")
                        response = None

                    if response:
                        return bytes(HTTP() / HTTPResponse(Status_Code=str(response.status_code)) / Raw(
                            load=response.content.decode('ascii')))
                    else:
                        return bytes(HTTP / HTTPResponse(Status_Code='405') / Raw())
                else:
                    return bytes(HTTP / HTTPResponse(Status_Code='400') / Raw())
            else:
                return bytes(HTTP / HTTPResponse(Status_Code='400') / Raw())
        else:
            return bytes(HTTP / HTTPResponse(Status_Code='400') / Raw())

    def decide(self, function) -> str:
        with self.lock:
            if self.bestHosts.get(function):
                return self.bestHosts[function]
            else:
                return ""

    def updateAll(self):
        while self.isRunning:
            self.updateHosts()
            self.updateNetworkMetrics()
            self.updateFaasMetrics()
            self.updateBestHosts()
            sleep(self.pause)

    def updateHosts(self):
        print()
        print("=== Hosts updating ===")

        try:
            response = get("http://" + self.regServerIP + ":" + str(self.regServerPort) + "/Hosts")
            self.hosts = list(response.content.decode('ascii').split(' '))[:-1]
        except:
            print(">>> Hosts haven't been updated")

        print(self.hosts)

    def updateNetworkMetrics(self):
        print()
        print("=== Network metrics updating ===")

        maxMetrics = [0, 0]
        minMetrics = [0, 0]
        self.rttav.clear()
        self.hopav.clear()

        for targetIP in self.hosts:
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
            if self.rttav[targetIP] < self.maxrtt:
                if self.rttav[targetIP] > maxMetrics[0]:
                    maxMetrics[0] = self.rttav[targetIP]
                if self.rttav[targetIP] < minMetrics[0]:
                    minMetrics[0] = self.rttav[targetIP]
            else:
                pass

            sum = 0
            for hop in self.hop[targetIP]:
                sum += hop
            self.hopav[targetIP] = sum / len(self.hop[targetIP])
            if self.hopav[targetIP] < self.maxhop:
                if self.hopav[targetIP] > maxMetrics[1]:
                    maxMetrics[1] = self.hopav[targetIP]
                if self.hopav[targetIP] < minMetrics[1]:
                    minMetrics[1] = self.hopav[targetIP]
            else:
                pass

            # unreachable hosts removing
            if self.rttav[targetIP] >= self.maxrtt or self.hopav[targetIP] >= self.maxhop:
                self.hosts.remove(targetIP)
                self.rttav.pop(targetIP)
                self.hopav.pop(targetIP)

        print(dumps(self.rttav, indent=2, sort_keys=True))
        print(dumps(self.hopav, indent=2, sort_keys=True))

        # data collecting
        for host in serverless_hosts:
            if not metrics_values.get(host):
                metrics_values[host] = defaultdict(list)

            if self.rttav.get(host):
                metrics_values[host][network_metrics_names[0]].append(self.rttav[host])
            else:
                metrics_values[host][network_metrics_names[0]].append(0)

            if self.hopav.get(host):
                metrics_values[host][network_metrics_names[1]].append(self.hopav[host])
            else:
                metrics_values[host][network_metrics_names[1]].append(0)

        # normalization
        for host, metric in self.rttav.items():
            if maxMetrics[0] - minMetrics[0] > 0:
                self.rttav[host] = (self.rttav[host] - minMetrics[0]) / (maxMetrics[0] - minMetrics[0])
            else:
                self.rttav[host] = 1

        for host, metric in self.hopav.items():
            if maxMetrics[1] - minMetrics[1] > 0:
                self.hopav[host] = (self.hopav[host] - minMetrics[1]) / (maxMetrics[1] - minMetrics[1])
            else:
                self.hopav[host] = 1

    def ping(self, targetIP):
        start = time()
        ans, unans = sr(IP(dst=targetIP, ttl=64) / ICMP(), timeout=2)
        if not unans and (ans[0][1][ICMP].type == 8 or ans[0][1][ICMP].type == 0):
            return 1000 * (time() - start), 64 - ans[0][1][IP].ttl + 1
        else:
            return self.maxrtt, self.maxhop

    def updateFaasMetrics(self):
        print()
        print("=== Faas metrics updating ===")

        maxMetrics = dict()
        minMetrics = dict()
        self.faasMetrics.clear()
        for host in self.hosts:
            global response
            try:
                response = get("http://" + host + ":" + str(self.faasPort) + "/Metrics")
            except:
                print(">>>", host, "metrics haven't been updated")
                for function in self.faasMetrics.keys():
                    if self.faasMetrics[function].get(host):
                        self.faasMetrics[function].pop(host)
                continue
            faasmetrics = loads(response.content.decode('ascii'))

            # print(dumps(faasmetrics, indent=2, sort_keys=True))

            for function, metrics in faasmetrics.items():

                if not maxMetrics.get(function):
                    maxMetrics[function] = dict()
                    for name in self.faasMetricsNames:
                        maxMetrics[function][name] = float(0)

                if not minMetrics.get(function):
                    minMetrics[function] = dict()
                    for name in self.faasMetricsNames:
                        minMetrics[function][name] = float(0)

                for name, value in metrics.items():
                    if metrics[name] > maxMetrics[function][name]:
                        maxMetrics[function][name] = metrics[name]
                    if metrics[name] < minMetrics[function][name]:
                        minMetrics[function][name] = metrics[name]

                    self.faasMetrics[function][host] = metrics

        print(dumps(dict(self.faasMetrics), indent=2, sort_keys=True))

        # data collecting
        for host in serverless_hosts:
            if not metrics_values.get(host):
                metrics_values[host] = defaultdict(list)

            for i in range(3):
                if self.faasMetrics.get('figlet') and self.faasMetrics['figlet'].get(host):
                    metrics_values[host][faas_metrics_names[i]].append(
                        self.faasMetrics['figlet'][host][self.faasMetricsNames[i]])
                else:
                    metrics_values[host][faas_metrics_names[i]].append(0)

        # normalization
        for function, hosts in self.faasMetrics.items():
            for host, metrics in hosts.items():
                for name, value in metrics.items():
                    if (maxMetrics[function][name] - minMetrics[function][name]) > 0:
                        self.faasMetrics[function][host][name] = (self.faasMetrics[function][host][name] -
                                                                  minMetrics[function][name]) / (
                                                                         maxMetrics[function][name] -
                                                                         minMetrics[function][name])
                    else:
                        self.faasMetrics[function][host][name] = 1.0

    def updateBestHosts(self):
        print()
        print("=== The best hosts updating ===")

        # data collecting
        time_line.append(time() - start_time)

        with self.lock:
            self.bestHosts.clear()
        for function in self.faasMetrics.keys():
            targetValues = dict()
            for host in self.hosts:
                targetValues[self.targetFunction(function, host)] = host

            print(function, dumps(targetValues, indent=2, sort_keys=True))

            try:
                value = min(targetValues.keys())
                with self.lock:
                    self.bestHosts[function] = targetValues[value]
            except:
                with self.lock:
                    self.bestHosts[function] = ""

        # data collecting
        with self.lock:
            if self.bestHosts.get('figlet'):
                best_hosts.append(self.bestHosts['figlet'])
            else:
                best_hosts.append("")

        with self.lock:
            print(dumps(dict(self.bestHosts), indent=2, sort_keys=True))

    def targetFunction(self, function, host):
        sum = 0
        if self.rttav.get(host):
            sum += self.rttav[host]
        else:
            sum += 2.0
        if self.hop.get(host):
            sum += self.hopav[host]
        else:
            sum += 2.0

        for name in self.faasMetricsNames:
            if self.faasMetrics[function].get(host) and self.faasMetrics[function][host].get(name):
                sum += self.faasMetrics[function][host][name]
            else:
                sum += 2.0
        return sum


class HTTPRequestHandler(BaseHTTPRequestHandler):

    def handle(self):
        self.data = self.request.recv(1024).strip()
        try:
            response = self.server.handle(self.data)
            self.request.sendall(response)
        except:
            self.send_response(400)
            self.send_header('content-type', 'text/html')
            self.end_headers()
            self.wfile.write("Handling error!")


def saveResults():
    colors = ['b', 'g', 'r']
    if not path.exists('./pictures/'):
        os.mkdir('./pictures/')
    if not path.exists('./results/'):
        os.mkdir('./results/')
    p_path = './pictures/'
    r_path = './results/'
    if not kill_reg:
        p_path += '1/'
        r_path += '1/'

        if not path.exists('./pictures/1'):
            os.mkdir('./pictures/1')
        if not path.exists('./results/1'):
            os.mkdir('./results/1')
    else:
        p_path += '2/'
        r_path += '2/'

        if not path.exists('./pictures/2/'):
            os.mkdir('./pictures/2/')
        if not path.exists('./results/2/'):
            os.mkdir('./results/2/')

    with open(r_path + "results.txt", 'w') as out:
        out.write(dumps(metrics_values, indent=2))
        out.write(str(time_line) + '\n')
        out.write(str(times) + '\n')
        out.write(str(best_hosts) + '\n')

    # FaaS metrics
    fig, axes = plt.subplots(nrows=3, ncols=1)
    name = 'FaaS metrics'
    for i, ax in enumerate(fig.axes):
        for j, host in enumerate(serverless_hosts):
            ax.plot(time_line, metrics_values[host][faas_metrics_names[i]], colors[j] + '-', linewidth=1, label=host)
        ax.set_ylabel(faas_metrics_names[i])
        ax.grid(True)
        for t in times:
            ax.axvline(t, color='r')
    plt.legend()
    plt.xlabel('Время, с')
    plt.savefig(p_path + name + str(1000 * rate) + '.pdf')
    plt.close()

    # Network metrics
    fig, axes = plt.subplots(nrows=2, ncols=1)
    name = 'Network metrics'
    for i, ax in enumerate(fig.axes):
        for j, host in enumerate(serverless_hosts):
            ax.plot(time_line, metrics_values[host][network_metrics_names[i]], colors[j] + '-', linewidth=1,
                    label=host)
        ax.set_ylabel(network_metrics_names[i])
        ax.grid(True)
        for t in times:
            ax.axvline(t, color='r')
    plt.legend()
    plt.xlabel('Время, с')
    plt.savefig(p_path + name + str(1000 * rate) + '.pdf')
    plt.close()

    # Best host
    name = 'Best hosts'
    plt.plot(time_line, best_hosts, 'b.', linewidth=1)
    for t in times:
        plt.axvline(t, color='r')
    plt.grid(True)
    # plt.ylabel('IP-адрес конченой бессерверной платформы')
    plt.xlabel('Время, с')
    plt.savefig(p_path + name + str(1000 * rate) + '.pdf')
    plt.close()


def signalHandler(signum, frame):
    # experiment
    global server_state
    if server_state == 'start':
        print("**** State:", server_state)
        if kill_reg:
            response = get(url="http://10.0.5.1:8080/Shutdown")
            print("**** Time:", float(response.content.decode('ascii')) - start_time)
            times.append(float(response.content.decode('ascii')) - start_time)
        server_state = 'terminate registration'
        alarm(10)
        return

    elif server_state == 'terminate registration':
        print("**** State:", server_state)
        response = get(url="http://10.0.1.1:8888/Shutdown")
        print("**** Time:", float(response.content.decode('ascii')) - start_time)
        times.append(float(response.content.decode('ascii')) - start_time)
        server_state = 'terminate serverless'
        alarm(10)
        return

    elif server_state == 'terminate serverless':
        print("**** State:", server_state)
        response = None
        while not response:
            try:
                response = get(url="http://10.0.1.1:8888/Run")
            except:
                pass
        print("**** Time:", float(response.content.decode('ascii')) - start_time)
        times.append(float(response.content.decode('ascii')) - start_time)
        server_state = 'run serverless'
        alarm(10)
        return

    elif server_state == 'run serverless':
        print("**** State:", server_state)
        raise Exception("Shutdown")

    # raise Exception("Shutdown")


if __name__ == '__main__':
    print()
    print('=== Decider starting ===')
    alarm(10)
    signal(SIGALRM, signalHandler)
    signal(SIGINT, signalHandler)

    deciderIP = '10.0.4.2'
    deciderPort = 8080
    faasPort = 8888
    regServerIP = '10.0.5.1'
    regServerPort = 8080

    decider = Decider(deciderIP, deciderPort, faasPort, regServerIP, regServerPort, rate)

    try:
        decider.start()

    except:
        pass

    finally:

        # data saving
        saveResults()

        print()
        print('=== Decider stopping ===')
        decider.finish()
