#!/bin/bash
set -e

if [ ! -d "myenv" ]; then
    python3 -m venv myenv
fi

source myenv/bin/activate
pip install --upgrade pip --quiet
pip install easyocr google-genai pynput colorama pillow --quiet

echo "Setup completed."
