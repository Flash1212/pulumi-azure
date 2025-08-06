#! /usr/bin/bash

# PowerShell script to set up the environment for AZ-204 exam preparation
# This script installs apache, and some common development tools.

function install_apt_apps {
    echo "Installing applications via apt..."
    add-apt-repository ppa:git-core/ppa # for latest git. Comment if not needed
    apt update
    apt-get install -y git python3 apache2 php libapache2-mod-php
    chmod 755 /var/www/html
    echo "Apt applications have been installed."
}

setup_output=/var/log/az204-setup.log
install_apt_apps > "$setup_output"
