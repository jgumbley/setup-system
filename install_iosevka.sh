#!/bin/bash

# Download the Iosevka font
wget http://sid.ethz.ch/debian/fonts-iosevka/pool/main/f/fonts-iosevka/fonts-iosevka_27.1.0.orig.tar.xz

# Extract the font archive
tar -xf fonts-iosevka_27.1.0.orig.tar.xz

# Create the local font directory if it doesn't exist
mkdir -p ~/.fonts

# Copy the font files to the local font directory
cp -r fonts-iosevka_27.1.0/ ~/.fonts/

# Update the font cache
fc-cache -f -v

