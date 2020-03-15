from mininet.net import Mininet
from mininet.topo import SingleSwitchTopo, Topo
from mininet.node import OVSSwitch, RemoteController, Node
from mininet.cli import CLI
from mininet.link import OVSLink, OVSIntf, Intf
from mininet.log import setLogLevel, info


class NetworkTopo(Topo):

    def build(self, **_opts):
        print("*** Add switches and hosts ***")
        s1 = net.addSwitch('s1')
        h1 = net.addHost('h1')
        h2 = net.addHost('h2')
        c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)

        print("*** Add links ***")
        l1 = net.addLink(h1, s1)
        l2 = net.addLink(h2, s1)

        print("*** Add external interfaces ***")
        _intf = Intf('enp0s3', s1)


def run():
    print("*** Create a network ***")
    net = Mininet(topo=NetworkTopo(), switch=OVSSwitch, link=OVSLink, controller=RemoteController)

    print("*** Start controller ***")
    c0.start()
    s1.start([c0])

    print("*** Start network ***")
    net.build()
    net.start()

    print("*** Delete interfaces and lease DHCP addresses ***")
    net.getNodeByName('h1').cmd("sudo dhclient -r && sudo dhclient")
    net.getNodeByName('h2').cmd("sudo dhclient -r && sudo dhclient")

    print("*** Start CLI ***")
    CLI(net)

    print("*** Stop network ***")
    net.stop()


def main():
    setLogLevel('info')
    run()


if __name__ == '__main__':
    main()