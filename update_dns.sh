#!/bin/bash
#
MYIP=`curl http://checkip.amazonaws.com`

# This POST command updates DNS record of domain
# These are example values - change to your Dynu account API key and domain
# Copy this file to /usr/local/bin when edited and chmod +x if necessary

curl -X POST https://api.dynu.com/v2/dns/100345616 \
	-H "accept:application/json" \
	-H "API-Key: f123456789123456789f" \
	--json '{"name": "mydomain.org","group": "","ipv4Address": "'$MYIP'","ipv6Address": "","ttl": 90, "ipv4": true,"ipv6": false,"ipv4WildcardAlias": true,"ipv6WildcardAlias": false,"allowZoneTransfer": false,"dnssec": false}'
