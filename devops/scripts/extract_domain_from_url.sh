#!/bin/bash

# This script is designed to be `source`d to create reusable helper functions

function extract_domain_from_url()
{
  url=$1
  
  # Remove protocol (http:// or https://)
  domain=$(echo "$url" | sed -E 's|^https?://||')
  
  # Remove path and query parameters (everything after the first /)
  domain=$(echo "$domain" | sed 's|/.*||')
  
  # Remove port if present (everything after the first :)
  domain=$(echo "$domain" | sed 's|:.*||')
  
  echo "$domain"
}