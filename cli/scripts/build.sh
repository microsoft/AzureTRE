#!/bin/bash
set -e


echo "Cleaning build/dist folders..."
rm -rf build
rm -rf dist

echo "Running build..."
pip install build
python -m build

echo "Done."