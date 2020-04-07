#!/usr/bin/env bash

echo kek | faas-cli --gateway 10.0.8.52:8080 invoke figlet
#faas-cli --gateway 10.0.8.52:8080 invoke figlet < tmp
