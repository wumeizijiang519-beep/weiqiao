#!/usr/bin/env bash
set -euo pipefail
sudo -n docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' 1677369_gpu21
sudo -n docker ps --filter name=1677369_gpu21 --format '{{.ID}} {{.Names}} {{.Status}}'
