#!/bin/bash
# Morvis 설치 스크립트 (맥북, Apple Silicon)
set -e
cd "$(dirname "$0")"

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install sounddevice numpy requests mlx-whisper

echo
echo "설치 완료. 실행:"
echo "  cd $(pwd) && source .venv/bin/activate && python morvis.py"
