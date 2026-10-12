#!/bin/sh
set -eu

# Docker and EKS provide different DNS addresses. Read the container's resolver
# at startup rather than baking Docker's loopback address into an AWS image.
resolver=$(awk '$1 == "nameserver" { print $2; exit }' /etc/resolv.conf)
if ! printf '%s\n' "$resolver" | awk -F. 'NF != 4 {exit 1} {for(i=1;i<=4;i++) if ($i !~ /^[0-9]+$/ || $i > 255) exit 1}'; then
  printf '%s\n' 'A valid IPv4 container DNS resolver is required.' >&2
  exit 1
fi
api_upstream=${API_UPSTREAM:-api:8000}
if ! printf '%s\n' "$api_upstream" | grep -Eq '^[A-Za-z0-9][A-Za-z0-9.-]*:[0-9]{1,5}$'; then
  printf '%s\n' 'API_UPSTREAM must be one hostname and port.' >&2
  exit 1
fi
port=${api_upstream##*:}
if [ "$port" -lt 1 ] || [ "$port" -gt 65535 ]; then
  printf '%s\n' 'API_UPSTREAM port is invalid.' >&2
  exit 1
fi
sed -e "s/__RUNTIME_DNS_RESOLVER__/$resolver/g" -e "s/__RUNTIME_API_UPSTREAM__/$api_upstream/g" /etc/nginx/conf.d/default.conf > /tmp/northstar-server.conf
if [ "${LOCAL_STORAGE_PROXY_ENABLED:-true}" = "false" ]; then
  # AWS uses authenticated S3 URLs, not the Docker-only MinIO gateway.
  sed '/^  location \/storage\/ {$/,/^  }$/c\
  location /storage/ { return 404; }' /tmp/northstar-server.conf > /tmp/northstar-server-aws.conf
  mv /tmp/northstar-server-aws.conf /tmp/northstar-server.conf
fi
mkdir -p /tmp/nginx-client /tmp/nginx-proxy /tmp/nginx-fastcgi /tmp/nginx-uwsgi /tmp/nginx-scgi
: > /tmp/northstar-trusted-proxies.conf
: > /tmp/northstar-trusted-proxy-geo.conf
proxy_list=${TRUSTED_PROXY_CIDRS:-}
saved_ifs=$IFS
IFS=,
for cidr in $proxy_list; do
  if ! printf '%s\n' "$cidr" | awk -F'[./]' 'NF != 5 {exit 1} {for(i=1;i<=4;i++) if ($i !~ /^[0-9]+$/ || $i > 255) exit 1; if ($5 !~ /^[0-9]+$/ || $5 < 8 || $5 > 32) exit 1}'; then
    printf '%s\n' 'TRUSTED_PROXY_CIDRS must contain specific IPv4 CIDRs (/8 through /32).' >&2
    exit 1
  fi
  printf 'set_real_ip_from %s;\n' "$cidr" >> /tmp/northstar-trusted-proxies.conf
  printf '%s 1;\n' "$cidr" >> /tmp/northstar-trusted-proxy-geo.conf
done
IFS=$saved_ifs
cat > /tmp/northstar-main.conf <<'CONFIG'
pid /tmp/nginx.pid;
error_log /dev/stderr warn;
events { worker_connections 1024; }
http {
  include /etc/nginx/mime.types;
  default_type application/octet-stream;
  access_log /dev/stdout;
  sendfile on;
  client_body_temp_path /tmp/nginx-client;
  proxy_temp_path /tmp/nginx-proxy;
  fastcgi_temp_path /tmp/nginx-fastcgi;
  uwsgi_temp_path /tmp/nginx-uwsgi;
  scgi_temp_path /tmp/nginx-scgi;
  include /tmp/northstar-trusted-proxies.conf;
  real_ip_header X-Forwarded-For;
  real_ip_recursive on;
  geo $realip_remote_addr $northstar_trusted_proxy {
    default 0;
    include /tmp/northstar-trusted-proxy-geo.conf;
  }
  map "$northstar_trusted_proxy:$http_x_forwarded_proto" $northstar_proxy_scheme {
    default $scheme;
    "1:https" https;
    "1:http" http;
  }
  include /tmp/northstar-server.conf;
}
CONFIG
exec nginx -c /tmp/northstar-main.conf "$@"
