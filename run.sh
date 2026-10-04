#!/bin/bash
cd "$(dirname "$0")"

if [ ! -d "myenv" ]; then
    echo "Error: 'myenv' not found. Run ./install_env.sh first."
    exit 1
fi

source myenv/bin/activate
python3 assistant.py