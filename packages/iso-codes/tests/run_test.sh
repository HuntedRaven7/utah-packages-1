#!/bin/bash

# If one of the commands below returns non-zero then exit immediately
set -e

echo "Let's check the upstream data files timestamp"
ls data/iso*.json -l
echo "Validating json data files written with correct syntax"
python3 bin/validate_json_data.py
retval=$?
if [ $retval -ne 0 ]; then
        echo "FAILED: Validation of data files"
else
        echo "PASSED: Validation of data files"
fi

echo "Let's check timestamp of newly generated data files"
ls data/iso*.json -l
