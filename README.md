# stevegizmo
Code to set up simple server that sends messages via the Rockblock GPS chip gizmo

## Provisioning the AWS server

* The server itself

Log into AWS Console and start an Ubuntu micro instance
Make sure TCP Port 5000 has an inbound rule (in the Security tab)
I also paid for the domain 'timeswine.org' through Dynu

* Apache2 server prep

First, install apache2 with

```
sudo apt install apache2
sudo apt install apache2-dev
sudo apt install libapache2-mod-wsgi-py3
```

These commands add ubuntu to the www-data group, make the /var/www directory group writeable, create a python virtualenv, and grabs the code for this project from Github:
```
sudo usermod -a -G www-data ubuntu
sudo chmod 775 /var/www
cd /var/www
python3 -m venv www-env
source www-env/bin/activate
git clone https://github.com/jmoonware/stevegizmo
```

Install the dash, dash-bootstrap-components, and mod\_wsgi python libs

* Dynamic DNS support

Each time the AWS server reboots it gets a new IP address (unless you are payingfor a static IP address...) So we need to set up a DNS record update on reboot. The simplest way appears to be a one-shot service using systemd.

See the update_dns.sh file and updatedns.service files in this repo. Copy the updatedns.service file to /etc/systemd/services and the update_dns.sh script to /usr/local/bin (after you edit the contents for accuracy.)

* Sending messages

The Rockblock device can call the url endpoint http://rockblock.timeswine.org:5000/receive. If the endpoint is called correctly, a notification is sent to subscribers and the message is logged and stored in the message store (a flat file.) 

Amazon SES (Simple Email Service) is used to notify subscribers. Note that setting up the CNAME and TXT DNS records is required (the records are provided by Amazon, although only as name/value pairs, and each DNS registrar has different names for the fields in e.g. CNAME records...)
Also, in SES 'sandbox' mode, emails can only be sent to verified email addresses (so each recipient will have to opt-in at some point.) To send texts, most carriers have an email gateway like <number>@txt.att.net.
