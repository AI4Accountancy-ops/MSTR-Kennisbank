#!/bin/sh
set -e

# Replace runtime variables in the runtime config JS file
if [ -n "$RUNTIME_API_URL" ]; then
  sed -i "s|RUNTIME_API_URL|$RUNTIME_API_URL|g" /usr/share/nginx/html/runtime-config.js
else
  # If not set, use a default or empty string
  sed -i "s|RUNTIME_API_URL||g" /usr/share/nginx/html/runtime-config.js
fi

# Continue with the regular nginx command
exec "$@" 