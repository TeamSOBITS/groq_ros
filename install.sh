#!/bin/bash
sudo apt update
pip3 install numpy==1.24.2  --break-system-packages
pip3 install -q -U groq  --break-system-packages