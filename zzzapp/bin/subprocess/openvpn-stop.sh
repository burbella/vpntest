#!/bin/bash
#-----stops OpenVPN-----
systemctl stop openvpn-server@server
systemctl stop openvpn-server@server-dns
systemctl stop openvpn-server@server-filtered
systemctl stop openvpn-server@server-icap
systemctl stop openvpn-server@server-squid
