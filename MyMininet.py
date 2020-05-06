#!/usr/bin/python

import os
from mininet.net import Mininet
from mininet.topo import Topo, SingleSwitchTopo
from mininet.node import OVSSwitch, RemoteController, Node
from mininet.cli import CLI
from mininet.link import OVSLink, Intf
from mininet.log import setLogLevel, info


class LinuxRouter(Node):
    """A Node with IP forwarding enabled."""

    def config(self, **params):
        super(LinuxRouter, self).config(**params)
        self.cmd('sysctl net.ipv4.ip_forward=1')

    def terminate(self):
        self.cmd('sysctl net.ipv4.ip_forward=0')
        super(LinuxRouter, self).terminate()


class NetworkTopo(Topo):
    """Two Linux Routers (Quagga) are each connected to a host."""

    def build(self, **_opts):
        info("### Adding routers and hosts \n")
        r1 = self.addNode('r1', cls=LinuxRouter)
        r2 = self.addNode('r2', cls=LinuxRouter)
        r3 = self.addNode('r3', cls=LinuxRouter)
        r4 = self.addNode('r4', cls=LinuxRouter)
        r5 = self.addNode('r5', cls=LinuxRouter)

        h1 = self.addHost('h1', ip='10.0.4.1/24', defaultRoute='via 10.0.4.2')
        h2 = self.addHost('h2', ip='10.0.5.1/24', defaultRoute='via 10.0.5.2')

        info("### Add links")
        l1 = self.addLink(r1, r2, intfName1='r1-eth2', intfName2='r2-eth1')
        l2 = self.addLink(r2, r3, intfName1='r2-eth3', intfName2='r3-eth1')
        l3 = self.addLink(r2, r4, intfName1='r2-eth4', intfName2='r4-eth1')
        l4 = self.addLink(r4, r5, intfName1='r4-eth2', intfName2='r5-eth1')
        l5 = self.addLink(h1, r1, intfName1='h1-eth1', intfName2='r1-eth1')
        l6 = self.addLink(h2, r2, intfName1='h2-eth1', intfName2='r2-eth2')


def SetQuagga(Router):
    """Start zebra and ospfd."""

    Router.cmd('sudo /usr/local/sbin/zebra -f conf/%s-zebra.conf -d -i /tmp/%s-zebra.pid -z /tmp/%s-zebra.api'
               % (Router.name, Router.name, Router.name), shell=True)
    Router.waitOutput()

    # Router.cmd(
    #     '/usr/local/sbin/ospfd -f conf/%s-ospfd.conf -d -i /tmp/%s-ospfd.pid -z /tmp/%s-zebra.api'
    #     % (Router.name, Router.name, Router.name), shell=True)
    # Router.waitOutput()


def run():
    info("### Create a network \n")
    net = Mininet(topo=NetworkTopo(), controller=None)

    info("### Start network \n")
    net.start()

    info("### Getting nodes \n")
    r = {i: net.getNodeByName('r' + str(i)) for i in range(1, 6)}
    h1 = net.getNodeByName('h1')
    h2 = net.getNodeByName('h2')

    info("### Add addresses \n")
    for i in range(2, 6):
        r[i].setIP(ip="10.0.{}.1".format(i + 4), prefixLen=24, intf="r{}-eth1".format(i))
    r[1].setIP(ip="10.0.4.2", prefixLen=24, intf="r1-eth1")
    r[1].setIP(ip="10.0.6.2", prefixLen=24, intf="r1-eth2")
    r[2].setIP(ip="10.0.5.2", prefixLen=24, intf="r2-eth2")
    r[2].setIP(ip="10.0.7.3", prefixLen=24, intf="r2-eth3")
    r[2].setIP(ip="10.0.8.4", prefixLen=24, intf="r2-eth4")
    r[4].setIP(ip="10.0.9.2", prefixLen=24, intf="r4-eth2")
    for k, v in r.items():
        print(k, v.__repr__())

    info("### Routes adding \n")
    r[1].cmd('ip route add 10.0.0.0/16 via 10.0.6.1')
    r[2].cmd('ip route add 10.0.4.0/24 via 10.0.6.2')
    r[2].cmd('ip route add 10.0.2.0/24 via 10.0.7.1')
    r[2].cmd('ip route add 10.0.3.0/24 via 10.0.8.1')
    r[2].cmd('ip route add 10.0.9.0/24 via 10.0.8.1')
    r[3].cmd('ip route add 10.0.0.0/16 via 10.0.7.3')
    r[4].cmd('ip route add 10.0.0.0/16 via 10.0.8.4')
    r[4].cmd('ip route add 10.0.3.0/24 via 10.0.9.1')
    r[5].cmd('ip route add 10.0.0.0/16 via 10.0.9.2')

    info("### Starting Quagga \n")
    for i in range(1, 6):
        SetQuagga(r[i])

    info("### Add external interfaces \n")
    intf1 = Intf(name='enp0s8', node=r[2], ip='10.0.1.2/24')
    intf2 = Intf(name='enp0s9', node=r[3], ip='10.0.2.2/24')
    intf3 = Intf(name='enp0s10', node=r[5], ip='10.0.3.2/24')

    CLI(net)

    info("### Stoping network \n")
    net.stop()

    os.system('killall -9 zebra')


def main():
    setLogLevel('info')
    run()


if __name__ == '__main__':
    main()
