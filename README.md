This is an experimental Proof of Concept script and configuration files used to disable the functionality of vulnerable IoT devices by exploiting a weakness in their heartbeat messages.
We used Bind9 DNS server and set it as the primary server of our LAN. We configured it to respond to the DNS queries from the hubs with our machine’s address instead of the heartbeat server. The named.confi file is the main configuration file of Bind9. It defines the zone files the correspond to each domain.
All zone files are similar, thus we only present the zone file that corresponds to Swann as an example.

This was developed as part of an MSc. project in the University of Kent in the UK.

Research Paper: Selective Forwarding Attack on IoT Home Security Kits

DOI: [10.1007/978-3-030-42048-2_23](https://link.springer.com/chapter/10.1007/978-3-030-42048-2_23)
