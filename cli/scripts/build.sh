#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset


echo "Cleaning build/dist folders..."
rm -rf build
rm -rf dist

echo "Running build..."
pip install build
python -m build

echo "Done."