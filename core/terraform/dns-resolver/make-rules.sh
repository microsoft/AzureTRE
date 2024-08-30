#!/bin/bash
#
# Generate a JSON object with the DNS rules for the private resolver
#

cd $(dirname $(realpath $0))

resolver="8.8.8.8" # Google, is there a better choice?
i=0

echo "{"
for domain in $(cat dns-whitelist.txt | sed -e 's%#.*$%%')
do
  echo "    \"rule_${i}\": \"{ \\\"address\\\": \\\"${resolver}\\\", \\\"domain\\\": \\\"${domain}.\\\" }\","
  i=$(( i + 1 ))
done

echo "    \"sink\": \"{  \\\"address\\\": \\\"0.0.0.0\\\", \\\"domain\\\": \\\".\\\" }\""
echo "}"
