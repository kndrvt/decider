import ciscotelnet

ciscotelnet.WAIT_TIMEOUT = 60
with ciscotelnet.CiscoTelnet(host="127.0.0.1", port=2605, verbose=False) as cisco:
    cisco.set_debuglevel(0)
    if cisco.login(final_mode=ciscotelnet.MODE_ENABLE, line_pass="zebra", enable_pass="zebra"):
        print cisco.cmd("sh ip bgp")
        print ""
