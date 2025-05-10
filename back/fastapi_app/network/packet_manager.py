from scapy.all import IP, TCP, UDP, ICMP, Raw, Ether, ARP
from scapy.packet import Packet
from typing import Dict, Optional
import subprocess

class PacketManager:
    @staticmethod
    def create_packet(packet_config: Dict) -> Optional[Packet]:
        """Создает пакет на основе конфигурации"""
        layers = []
        
        if 'eth' in packet_config:
            layers.append(Ether(
                src=packet_config['eth'].get('src'),
                dst=packet_config['eth'].get('dst')
            ))
        
        if 'arp' in packet_config:
            layers.append(ARP(
                psrc=packet_config['arp'].get('psrc'),
                pdst=packet_config['arp'].get('pdst'),
                hwsrc=packet_config['arp'].get('hwsrc'),
                hwdst=packet_config['arp'].get('hwdst'),
                op=packet_config['arp'].get('op', 1)
            ))
        
        if 'ip' in packet_config:
            layers.append(IP(
                src=packet_config['ip'].get('src'),
                dst=packet_config['ip'].get('dst'),
                ttl=packet_config['ip'].get('ttl', 64)
            ))
        
        if 'tcp' in packet_config:
            layers.append(TCP(
                sport=packet_config['tcp'].get('sport'),
                dport=packet_config['tcp'].get('dport'),
                flags=packet_config['tcp'].get('flags', 'S')
            ))
            
        elif 'udp' in packet_config:
            layers.append(UDP(
                sport=packet_config['udp'].get('sport'),
                dport=packet_config['udp'].get('dport')
            ))
        elif 'icmp' in packet_config:
            layers.append(ICMP(
                type=packet_config['icmp'].get('type', 8),
                code=packet_config['icmp'].get('code', 0)
            ))
        
        if 'payload' in packet_config:
            layers.append(Raw(load=packet_config['payload']))
        
        if not layers:
            return None
            
        packet = layers[0]
        for layer in layers[1:]:
            packet = packet/layer
            
        return packet

    @staticmethod
    def send_packet(node, packet: Packet, iface: Optional[str] = None, count: int = 1):
        """Отправляет пакет от конкретного узла"""
        packet_cmd = f"packet = {packet.command()}"
        
        if iface:
            send_cmd = f"sendp(packet, iface='{iface}', count={count})"
        else:
            send_cmd = f"send(packet, count={count})"
        
        cmd = f'python3 -c "from scapy.all import *; {packet_cmd}; {send_cmd}"'
        
        node.cmd(cmd)

    @staticmethod
    def ping(source_node, dest_ip: str, count: int = 1):
        """Отправляет ICMP пинг от узла источника к целевому IP"""
        cmd = f'ping -c {count} {dest_ip}'
        return source_node.cmd(cmd)

    @staticmethod
    def tcp_connection(source_node, dest_ip: str, dest_port: int):
        """Пытается установить TCP-соединение от узла источника к целевому IP и порту"""
        cmd = f'nc -zv {dest_ip} {dest_port}'
        return source_node.cmd(cmd)

    @staticmethod
    def udp_send(source_node, dest_ip: str, dest_port: int, message: str):
        """Отправляет UDP-сообщение от узла источника к целевому IP и порту"""
        cmd = f'echo "{message}" | nc -u {dest_ip} {dest_port}'
        return source_node.cmd(cmd)

    @staticmethod
    def http_request(source_node, dest_ip: str, port: int = 80):
        """Отправляет HTTP GET-запрос от узла источника к целевому IP и порту"""
        cmd = f'curl -s http://{dest_ip}:{port}/'
        return source_node.cmd(cmd)