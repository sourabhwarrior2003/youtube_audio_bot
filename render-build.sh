#!/usr/bin/env bash
# exit on error
set -o errexit

# Install Node.js (using NodeSource setup for version 20)
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# Verify Node.js installation
node --version

# Now install Python dependencies
pip install -r requirements.txt