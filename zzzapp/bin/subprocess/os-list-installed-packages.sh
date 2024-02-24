#!/bin/bash
#-----list the OS packages installed-----
zgrep -h 'status installed' /var/log/dpkg.log* | sort -r
