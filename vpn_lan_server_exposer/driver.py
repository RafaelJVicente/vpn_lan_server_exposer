import socket
import time
from ipaddress import ip_address, ip_network, IPv4Network, IPv6Network, IPv4Address, IPv6Address
from threading import Thread, Lock
from typing import Set, Union, List


class ServerDriver:
    def __init__(self, in_port: int, out_port: int) -> None:
        self.__ip_pool: Set[Union[ip_address, IPv4Address, IPv6Address]] = set()
        self._local_ip: ip_address = ip_address(socket.gethostbyname(socket.gethostname()))
        self.__in_port: int = in_port
        self.__out_port: int = out_port

        self.__send_lock: Lock = Lock()
        self._active: bool = True
        Thread(target=self.__packet_receiver).start()

    def __packet_receiver(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as catcher:
            catcher.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            catcher.bind(("", self.__in_port))
            while self._active:
                data, address = catcher.recvfrom(60000)
                print(f"RECEIVED MSG[{address}]: [{len(data)}] {data}")
                self.__send_packet(data)

    def __send_packet(self, data) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            with self.__send_lock:
                for ip in self.__ip_pool:
                    print(f"SENDING MSG[{str(ip), self.__out_port}]: [{len(data)}] {data}")
                    server.sendto(data, (str(ip), self.__out_port))

    def _insert_ip(self, new_ip: ip_address) -> None:
        new_ip = ip_address(new_ip)
        with self.__send_lock:
            if new_ip not in self.__ip_pool:
                self.__ip_pool.add(new_ip)

    def _remove_ip(self, ip_to_remove: ip_address) -> None:
        ip_to_remove = ip_address(ip_to_remove)
        with self.__send_lock:
            if ip_to_remove in self.__ip_pool:
                self.__ip_pool.remove(ip_to_remove)


class BroadcastServerDriver(ServerDriver):
    def __init__(self, in_port: int, out_port: int, netmask: str = '24'):
        super().__init__(in_port, out_port)
        cidr_network: Union[IPv4Network, IPv6Network] = ip_network(f"{self._local_ip}/{netmask}", False)
        hosts = cidr_network.hosts()
        next(hosts)  # Exclude gateway
        for ip in hosts:
            self._insert_ip(ip)


class ListServerDriver(ServerDriver):
    def __init__(self, in_port: int, out_port: int, players_ips_list: List[ip_address]):
        super().__init__(in_port, out_port)
        for ip in players_ips_list:
            self._insert_ip(ip)


data_ini = b'Ready to play'
data_end = b'Close'


class ClientsServerDriver(ServerDriver):
    def __init__(self, in_port: int, out_port: int, client_port: int = 23456):
        super().__init__(in_port, out_port)
        self.__client_port = client_port
        Thread(target=self.__start_client).start()

    def __start_client(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
            client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            client.bind(("", self.__client_port))
            while self._active:
                data, address = client.recvfrom(60000)
                print(f"RECEIVED IP [{address}]: [{len(data)}] {data}")
                if data == data_ini:
                    self._insert_ip(ip_address(address[0]))
                elif data == data_end:
                    self._remove_ip(ip_address(address[0]))
                else:
                    raise ValueError('Bad input data')


class DriverClient:
    def __init__(self, server_ip: ip_address, server_port: int = 23456, timeout: float = 600):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            print(f"SENDING IP[{str(server_ip), server_port}]: [{len(data_ini)}] {data_ini}")
            server.sendto(data_ini, (str(server_ip), server_port))
            time.sleep(timeout)
            print(f"SENDING IP[{str(server_ip), server_port}]: [{len(data_ini)}] {data_ini}")
            server.sendto(data_end, (str(server_ip), server_port))


if __name__ == '__main__':
    players_ips = [ip_address('10.8.0.2'), ip_address('10.8.0.3')]
    # driver = ListServerDriver(20050, 2005, players_ips)
    driver = ClientsServerDriver(20050, 2005)
