# Transport Network Management System for Distributed Serverless Computing

## Usage

You need to have a network containing several hosts with launched OpenFaaS platform. An example with a topology is shown in the pictures.
  
- **OpenfaasServer.py** is launched at the hosts with the OpenFaaS platform. 
You should change the IP-addresses of the Registration server and current host. 
Current host IP-address you can set as a parameter.

- **RegistrationServer.py** is launched at some host. 
It receives registration requests and information about OpenFaaS platform hosts.

- **Decider.py** is launched at the edge device. It collects information about network and OpenFaaS platforms.
It receives a list of platform from the Registration server. You should change IP-addresses of the Registration server 
and the current device.

When all scripts are launched, the client host can send requests for OpenFaaS platforms to the edge device.
**Decider.py** computes destination OpenFaaS platform for each request and redirects requests to according host.
  
![Setup](https://github.com/kndrvt/decider/blob/master/pictures/Setup.png)
  
![Topology](https://github.com/kndrvt/decider/blob/master/pictures/Topology.png)