#!/bin/bash
#-----starts OpenVPN-----
systemctl start openvpn-server@server
systemctl start openvpn-server@server-dns
systemctl start openvpn-server@server-filtered
systemctl start openvpn-server@server-icap
systemctl start openvpn-server@server-squid
