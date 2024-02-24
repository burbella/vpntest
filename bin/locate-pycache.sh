#!/bin/bash

#-----find pycache files that might be from the zzz project-----

locate __pycache__ | grep -vP '(dist\-packages|snap\/core|python3\.8|usr\/local\/bin|usr\/share|usr\/lib\/byobu)'
