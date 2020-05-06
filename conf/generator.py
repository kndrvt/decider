#!/usr/bin/python3

octets = [7, 10, 6, 8, 9]

for i in range(1, 6):
    with open("conf/r{}-ospfd.conf".format(i), 'w') as out:
        out.write("hostname ospfd\n")
        out.write("password zebra\n")
        out.write("enable password zebra\n")
        out.write("log file logs/r{}-ospfd.log\n".format(i))
        out.write("\n")
        out.write("router ospf\n")
        out.write("network 10.0.{}.0/24 area 0\n".format(i - 2 if i > 2 else i + 3))
        out.write("\n")

    with open("conf/r{}-zebra.conf".format(i), 'w') as out:
        out.write("hostname Router\n")
        out.write("password zebra\n")
        out.write("enable password zebra\n")
        out.write("log file logs/r{}-zebra.log\n".format(i))
        out.write("\n")
        out.write("interface lo\n")
        out.write("ip address 127.0.0.1/8\n")
        out.write("ip address 10.0.{}.1/32\n".format(i + 5))
        out.write("\n")
        out.write("interface r{}-eth1\n".format(i))
        out.write("ip address 10.0.{}.1/24\n".format(i + 5))
        out.write("\n")
        out.write("interface r{}-eth2\n".format(i))
        out.write("ip address 10.0.{}.2/24\n".format(octets[i - 1]))
        out.write("\n")
        if i < 3:
            out.write("interface r{}-eth3\n".format(i))
            out.write("ip address 10.0.{}.3/24\n".format(i + 3))
            out.write("\n")