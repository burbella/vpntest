#!/bin/bash

#-----restarts OpenVPN-----
systemctl restart openvpn-server@server
systemctl restart openvpn-server@server-dns
systemctl restart openvpn-server@server-filtered
systemctl restart openvpn-server@server-icap
systemctl restart openvpn-server@server-squid
