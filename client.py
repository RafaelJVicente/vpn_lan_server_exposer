from ipaddress import ip_address

from vpn_lan_server_exposer.driver import DriverClient

dc = DriverClient(ip_address('10.8.0.2'), timeout=5)
