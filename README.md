## stevegizmo
Code to set up simple server that sends messages via the Rockblock GPS chip gizmo

# Provisioning the AWS server

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
