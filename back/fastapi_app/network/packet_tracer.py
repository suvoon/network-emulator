from scapy.all import *
from typing import Dict, List, Optional
import asyncio
from django_app.models import PacketTrace
import time
import ipaddress
from ipaddress import IPv4Network, IPv4Address
import random
import socket

class PacketTracer:
    def __init__(self, topology_manager):
        self.topology_manager = topology_manager
        self.traces = {}
        
    def start_trace(self, trace_id, source, destination, packet_config):
        """Начинает трассировку пакета"""
        try:
            source_node = self.topology_manager.get_node(source)
            dest_node = self.topology_manager.get_node(destination)
            
            if not source_node or not dest_node:
                raise Exception(f"Source or destination node not found: {source if not source_node else ''} {destination if not dest_node else ''}")

            source_has_interfaces = True
            if not source_node.intfList() or len(source_node.intfList()) == 0:
                source_has_interfaces = False
                
                try:
                    intf_name = f"{source}-eth0"
                    source_node.cmd(f"ip link add {intf_name} type veth peer name sw-{intf_name}")
                    source_node.cmd(f"ip link set {intf_name} up")
                    
                    if source_node.intfList() and len(source_node.intfList()) > 0:
                        source_has_interfaces = True
                except Exception as intf_error:
                    pass
            
            dest_has_interfaces = True
            if not dest_node.intfList() or len(dest_node.intfList()) == 0:
                dest_has_interfaces = False
                
                try:
                    intf_name = f"{destination}-eth0"
                    dest_node.cmd(f"ip link add {intf_name} type veth peer name sw-{intf_name}")
                    dest_node.cmd(f"ip link set {intf_name} up")
                    
                    if dest_node.intfList() and len(dest_node.intfList()) > 0:
                        dest_has_interfaces = True
                except Exception as intf_error:
                    pass

            dest_ip = self._get_node_ip(dest_node)
            if not dest_ip:
                raise Exception(f"Destination node {destination} has no IP address")
                
            source_ip = self._get_node_ip(source_node)
            if not source_ip:
                raise Exception(f"Source node {source} has no IP address")
                
            try:
                if not self._verify_resolvable(source_ip.split('/')[0]):
                    pass
                    
                if not self._verify_resolvable(dest_ip.split('/')[0]):
                    pass
            except Exception as resolve_error:
                pass

            self.traces[trace_id] = {
                "source": source,
                "destination": destination,
                "source_ip": source_ip,
                "destination_ip": dest_ip,
                "current_node": source,
                "hops": [{
                    "node": source,
                    "time": time.time(),
                    "action": "start",
                    "details": f"Packet created from {source_ip} to {dest_ip}"
                }],
                "state": "in_progress",
                "error": None
            }

            protocol = packet_config.get('protocol', 'icmp')
            packet = None
            
            try:
                if protocol == 'icmp':
                    source_ip_clean = source_ip.split('/')[0]
                    dest_ip_clean = dest_ip.split('/')[0]
                    
                    try:
                        packet = IP(src=source_ip_clean, dst=dest_ip_clean)/ICMP()
                    except Exception as e:
                        raise Exception(f"Failed to create ICMP packet: {str(e)}")
                        
                elif protocol == 'tcp':
                    dport = packet_config.get('dport', 80)
                    sport = packet_config.get('sport', random.randint(1024, 65535))
                    source_ip_clean = source_ip.split('/')[0]
                    dest_ip_clean = dest_ip.split('/')[0]
                    
                    try:
                        packet = IP(src=source_ip_clean, dst=dest_ip_clean)/TCP(sport=sport, dport=dport)
                    except Exception as e:
                        raise Exception(f"Failed to create TCP packet: {str(e)}")
                        
                elif protocol == 'udp':
                    dport = packet_config.get('dport', 53)
                    sport = packet_config.get('sport', random.randint(1024, 65535))
                    payload = packet_config.get('payload', '')
                    source_ip_clean = source_ip.split('/')[0]
                    dest_ip_clean = dest_ip.split('/')[0]
                    
                    try:
                        packet = IP(src=source_ip_clean, dst=dest_ip_clean)/UDP(sport=sport, dport=dport)/Raw(load=payload)
                    except Exception as e:
                        raise Exception(f"Failed to create UDP packet: {str(e)}")
                        
                elif protocol == 'http':
                    dport = packet_config.get('dport', 80)
                    sport = packet_config.get('sport', random.randint(1024, 65535))
                    http_method = packet_config.get('method', 'GET')
                    path = packet_config.get('path', '/')
                    source_ip_clean = source_ip.split('/')[0]
                    dest_ip_clean = dest_ip.split('/')[0]
                    
                    try:
                        http_payload = f"{http_method} {path} HTTP/1.1\r\nHost: {dest_ip_clean}\r\n\r\n"
                        packet = IP(src=source_ip_clean, dst=dest_ip_clean)/TCP(sport=sport, dport=dport)/Raw(load=http_payload)
                    except Exception as e:
                        raise Exception(f"Failed to create HTTP packet: {str(e)}")
                        
                else:
                    raise Exception(f"Unsupported protocol: {protocol}")
            except Exception as packet_error:
                raise
            
            if not packet:
                raise Exception(f"Failed to create packet with protocol {protocol}")
            
            self.add_hop(trace_id, source, "send", f"Sending {protocol.upper()} packet from {source_ip} to {dest_ip}")

            try:
                route = self._trace_route(source_node, dest_node, packet)
                
                for hop in route:
                    self.add_hop(trace_id, hop['node'], hop['action'], hop['details'])

                self.complete_trace(trace_id, success=True)
            except Exception as route_error:
                self.complete_trace(trace_id, success=False, error=str(route_error))
                raise
            
        except Exception as e:
            self.complete_trace(trace_id, success=False, error=str(e))

    def _get_node_ip(self, node):
        """Получает IP-адрес для узла, обрабатывая как хосты, так и коммутаторы"""
        try:
            if not node:
                return None
                
            if hasattr(node, 'IP') and callable(node.IP):
                if not node.intfList() or len(node.intfList()) == 0:
                    if hasattr(self.topology_manager, 'active_topology') and self.topology_manager.active_topology:
                        active_topology = self.topology_manager.active_topology
                        for db_host in active_topology.hosts:
                            if db_host.get('name') == node.name and db_host.get('ip'):
                                db_ip = db_host['ip']
                                return db_ip
                                
                    return None
                
                try:
                    ip = node.IP()
                    if not ip or ip == '0.0.0.0':
                        if hasattr(self.topology_manager, 'active_topology') and self.topology_manager.active_topology:
                            active_topology = self.topology_manager.active_topology
                            for db_host in active_topology.hosts:
                                if db_host.get('name') == node.name and db_host.get('ip'):
                                    db_ip = db_host['ip']
                                    return db_ip
                        return None
                    
                    return f"{ip.split('/')[0] if '/' in ip else ip}/24"
                except Exception as ip_error:
                    return None
                    
            elif node.name.startswith('s'):
                ip = self.topology_manager.get_switch_ip(node.name)
                if not ip:
                    return None
                    
                return ip if '/' in ip else f"{ip}/24"
            
            elif node.name.startswith('r'):
                if hasattr(self.topology_manager, 'active_topology') and self.topology_manager.active_topology:
                    active_topology = self.topology_manager.active_topology
                    if hasattr(active_topology, 'routers'):
                        for router in active_topology.routers:
                            if router.get('name') == node.name:
                                if router.get('interfaces') and len(router['interfaces']) > 0:
                                    for intf in router['interfaces']:
                                        if 'ip' in intf and intf['ip']:
                                            return intf['ip']
                                if router.get('ip'):
                                    return router['ip']
                
            return None
            
        except Exception as e:
            return None

    def _trace_route(self, source_node, dest_node, packet):
        """Трассировка маршрута пакета через сеть"""
        route = []
        current = source_node
        visited = set([source_node.name])
        visited_subnets = set()
        
        max_hops = 20
        hop_count = 0

        dest_ip = packet.getlayer(IP).dst

        while current and hop_count < max_hops:
            hop_count += 1
            
            current_ip = None
            if not current.name.startswith('s'):
                current_ip = self._get_node_ip(current)
                if current_ip:
                    current_ip = current_ip.split('/')[0]
                    
                    if current.name.startswith('r'):
                        active_topology = None
                        if hasattr(self.topology_manager, 'active_topology') and self.topology_manager.active_topology:
                            active_topology = self.topology_manager.active_topology
                            
                        if active_topology and hasattr(active_topology, 'routers'):
                            for router in active_topology.routers:
                                if router.get('name') == current.name and router.get('interfaces'):
                                    router_subnets = []
                                    for intf in router['interfaces']:
                                        if intf.get('ip'):
                                            try:
                                                ip = intf['ip']
                                                ip_parts = ip.split('/') if '/' in ip else [ip, '24']
                                                ip_addr = ip_parts[0]
                                                mask = int(ip_parts[1]) if len(ip_parts) > 1 else 24
                                                
                                                network = IPv4Network(f"{ip_addr}/{mask}", strict=False)
                                                router_subnets.append(str(network))
                                            except Exception as e:
                                                pass
            
            if current.name == dest_node.name:
                route.append({
                    'node': current.name,
                    'action': 'receive',
                    'details': f'Пакет получен адресатом {dest_ip}'
                })
                break
            
            if current_ip and current_ip == dest_ip:
                route.append({
                    'node': current.name,
                    'action': 'receive',
                    'details': f'Пакет получен адресатом {dest_ip}'
                })
                break

            is_router = current.name.startswith('r')
            
            prev_node_name = None
            if len(route) > 0:
                prev_node_name = route[-1]['node']
            
            if is_router:
                next_hop, is_direct = self._find_router_next_hop(current, dest_ip)
            else:
                next_hop, is_direct = self._find_next_hop(current, dest_ip)
            
            if next_hop and next_hop.name in visited:
                route.append({
                    'node': current.name,
                    'action': 'loop',
                    'details': f'Обнаружена петля маршрутизации через {next_hop.name}'
                })
                break
            
            if next_hop:
                next_hop_ip = None
                if not next_hop.name.startswith('s'):
                    next_hop_ip = self._get_node_ip(next_hop)
                    if next_hop_ip:
                        next_hop_ip = next_hop_ip.split('/')[0]
                
                if is_router:
                    try:
                        subnet_mask = 24
                        for intf in next_hop.intfList():
                            if hasattr(intf, 'ip') and intf.ip == next_hop_ip:
                                subnet_mask = intf.prefixLen if hasattr(intf, 'prefixLen') else 24
                                break
                                
                        current_subnet = IPv4Network(f"{next_hop_ip if next_hop_ip else '0.0.0.0'}/{subnet_mask}", strict=False)
                        subnet_str = str(current_subnet)
                        
                        if subnet_str not in visited_subnets:
                            visited_subnets.add(subnet_str)
                            route.append({
                                'node': current.name,
                                'action': 'route',
                                'details': f'Маршрутизация в подсеть {subnet_str} через {next_hop.name}'
                            })
                    except Exception as e:
                        pass
                
                action_type = "forward"
                if is_direct and next_hop.name == dest_node.name:
                    action_type = "deliver" 
                
                details_ip = ""
                if next_hop_ip and not next_hop.name.startswith('s'):
                    details_ip = f" ({next_hop_ip})"
                
                route.append({
                    'node': current.name,
                    'action': action_type,
                    'details': f'Перенаправление к {next_hop.name}{details_ip}'
                })
                
                visited.add(next_hop.name)
                current = next_hop
            else:
                route.append({
                    'node': current.name,
                    'action': 'drop',
                    'details': f'Нет маршрута к адресату {dest_ip}'
                })
                break

        if hop_count >= max_hops:
            route.append({
                'node': current.name,
                'action': 'timeout',
                'details': f'Превышено максимальное количество хопов ({max_hops})'
            })

        return route

    def _find_next_hop(self, current_node, dest_ip):
        """Определяет следующий узел для перенаправления пакета на основе IP-адреса назначения"""
        dest_node = self.topology_manager.get_node_by_ip(dest_ip)
        
        came_from_node = None
        for trace_id, trace in self.traces.items():
            if trace["state"] == "in_progress":
                hops = trace["hops"]
                if len(hops) >= 2 and hops[-1]["node"] == current_node.name:
                    came_from_node = hops[-2]["node"]
                    break
        
        dest_network = None
        try:
            if '/' in dest_ip:
                dest_network = IPv4Network(dest_ip, strict=False)
            else:
                dest_network = IPv4Network(f"{dest_ip}/24", strict=False)
        except Exception as e:
            pass
            
        if current_node.name.startswith('h'):
            if dest_node and self._are_nodes_connected(current_node, dest_node):
                return dest_node, True
            
            gateways = []
            for intf in current_node.intfList():
                if intf.name != 'lo' and intf.link:
                    other_end = intf.link.intf2 if intf.link.intf1 == intf else intf.link.intf1
                    if came_from_node and other_end.node.name == came_from_node:
                        continue
                        
                    if other_end.node.name.startswith('r'):
                        gateways.insert(0, other_end.node)
                    elif other_end.node.name.startswith('s'):
                        gateways.append(other_end.node)
            
            if gateways:
                gateway = gateways[0]
                return gateway, False
                
            return None, False
        
        if current_node.name.startswith('s'):
            if dest_node and self._are_nodes_connected(current_node, dest_node):
                return dest_node, True
            
            connected_hosts = []
            connected_routers = []
            connected_switches = []
            
            for intf in current_node.intfList():
                if intf.name == 'lo' or not intf.link:
                    continue
                    
                other_end = intf.link.intf2 if intf.link.intf1 == intf else intf.link.intf1
                other_node = other_end.node
                
                if came_from_node and other_node.name == came_from_node:
                    continue
                
                if other_node.name.startswith('h'):
                    host_ip = self._get_node_ip(other_node)
                    if host_ip:
                        host_ip = host_ip.split('/')[0]
                        if host_ip == dest_ip:
                            return other_node, True
                    connected_hosts.append(other_node)
                elif other_node.name.startswith('r'):
                    connected_routers.append(other_node)
                elif other_node.name.startswith('s'):
                    connected_switches.append(other_node)
            
            if connected_routers:
                next_hop = connected_routers[0]
                return next_hop, False
            
            if connected_switches:
                next_hop = connected_switches[0]
                return next_hop, False
            
            if connected_hosts:
                next_hop = connected_hosts[0]
                return next_hop, False
        
        return None, False

    def _are_nodes_connected(self, node1, node2):
        """Проверяет, являются ли два узла непосредственно подключенными"""
        for intf1 in node1.intfList():
            if intf1.link:
                other_end = intf1.link.intf2 if intf1.link.intf1 == intf1 else intf1.link.intf1
                if other_end.node == node2:
                    return True
        return False

    def add_hop(self, trace_id, node, action, details=""):
        """Записывает прыжок в пути пакета"""
        if trace_id in self.traces:
            self.traces[trace_id]["hops"].append({
                "node": node,
                "time": time.time(),
                "action": action,
                "details": details
            })
            self.traces[trace_id]["current_node"] = node
            
    def complete_trace(self, trace_id, success=True, error=None):
        """Отмечает трассировку как завершенную"""
        if trace_id in self.traces:
            trace = self.traces[trace_id]
            trace["state"] = "completed"
            
            reached_destination = trace["current_node"] == trace["destination"]
            trace["success"] = success and reached_destination and not error
            
            if error:
                trace["error"] = error
            
            self.add_hop(
                trace_id,
                trace["current_node"],
                "end",
                "Success" if trace["success"] else f"Failed: {error or 'Did not reach destination'}"
            )
            
    def get_trace_info(self, trace_id):
        """Получает информацию о трассировке"""
        return self.traces.get(trace_id)

    def ping(self, source_node_name, destination_ip, count=1):
        """Пинг от источника к IP-адресу назначения"""
        results = []
        source_node = self.topology_manager.get_node(source_node_name)
        
        if not source_node:
            return {
                "success": False,
                "error": f"Source node {source_node_name} not found"
            }
            
        source_ip = self._get_node_ip(source_node)
        if not source_ip:
            return {
                "success": False,
                "error": f"Source node {source_node_name} has no IP address"
            }
            
        source_ip = source_ip.split('/')[0]

        if '/' in destination_ip:
            destination_ip = destination_ip.split('/')[0]
        
        for i in range(count):
            trace_id = f"ping-{time.time()}-{i}"
            
            packet_config = {
                "protocol": "icmp",
                "type": 8,
                "code": 0,
                "id": random.randint(1, 65535),
                "seq": i + 1
            }
            
            dest_node = self.topology_manager.get_node_by_ip(destination_ip)
            if not dest_node:
                for node_name, node in self.topology_manager.nodes.items():
                    node_ip = self._get_node_ip(node)
                    if node_ip and node_ip.split('/')[0] == destination_ip:
                        dest_node = node
                        break
                
            if dest_node:
                self.start_trace(trace_id, source_node_name, dest_node.name, packet_config)
                trace = self.get_trace_info(trace_id)
                
                if trace and trace.get("success", False):
                    start_time = None
                    end_time = None
                    
                    for hop in trace["hops"]:
                        if hop["action"] == "start":
                            start_time = hop["time"]
                        elif hop["action"] == "receive" and hop["node"] == dest_node.name:
                            end_time = hop["time"]
                    
                    rtt = (end_time - start_time) * 1000 if start_time and end_time else None
                    
                    results.append({
                        "seq": i + 1,
                        "success": True,
                        "time_ms": rtt,
                        "destination": destination_ip
                    })
                else:
                    results.append({
                        "seq": i + 1,
                        "success": False,
                        "error": trace.get("error", "Request timed out")
                    })
            else:
                results.append({
                    "seq": i + 1,
                    "success": False,
                    "error": f"No host with IP {destination_ip} found"
                })
        
        successes = sum(1 for r in results if r.get("success", False))
        
        return {
            "source": source_node_name,
            "source_ip": source_ip,
            "destination_ip": destination_ip,
            "packets_sent": count,
            "packets_received": successes,
            "packet_loss": (count - successes) / count * 100 if count > 0 else 100,
            "results": results
        }

    def _verify_resolvable(self, ip_address):
        """Проверяет, может ли IP-адрес быть разрешен по DNS или является действительным"""
        try:
            if not ip_address:
                return False
                
            if '/' in ip_address:
                ip_address = ip_address.split('/')[0]
                
            ipaddress.ip_address(ip_address)
            
            try:
                socket.gethostbyaddr(ip_address)
            except socket.herror:
                pass
                
            return True
        except ValueError:
            return False
        except Exception as e:
            return False

    def _find_router_next_hop(self, router_node, dest_ip):
        """Находит следующий узел для пакета на маршрутизаторе на основе его таблицы маршрутизации"""
        dest_node = self.topology_manager.get_node_by_ip(dest_ip)
        
        came_from_node = None
        for trace_id, trace in self.traces.items():
            if trace["state"] == "in_progress":
                hops = trace["hops"]
                if len(hops) >= 2 and hops[-1]["node"] == router_node.name:
                    came_from_node = hops[-2]["node"]
                    break
        
        active_topology = None
        if hasattr(self.topology_manager, 'active_topology') and self.topology_manager.active_topology:
            active_topology = self.topology_manager.active_topology
        
        router_interfaces = []
        router_networks = []
        if active_topology and hasattr(active_topology, 'routers'):
            for router in active_topology.routers:
                if router.get('name') == router_node.name and router.get('interfaces'):
                    for intf in router['interfaces']:
                        if intf.get('ip'):
                            ip = intf['ip']
                            interface_name = intf.get('name', '')
                            
                            router_interfaces.append({
                                'name': interface_name,
                                'ip': ip,
                                'subnet_mask': intf.get('subnet_mask', 24)
                            })
                            
                            try:
                                ip_parts = ip.split('/') if '/' in ip else [ip, '24']
                                ip_addr = ip_parts[0]
                                mask = int(ip_parts[1]) if len(ip_parts) > 1 else 24
                                
                                network = IPv4Network(f"{ip_addr}/{mask}", strict=False)
                                router_networks.append({
                                    'network': network,
                                    'interface': interface_name,
                                    'ip': ip_addr
                                })
                            except Exception as e:
                                pass
        
        dest_ip_obj = None
        try:
            dest_ip_obj = IPv4Address(dest_ip)
        except Exception as e:
            pass
        
        dest_in_direct_network = False
        dest_network_info = None
        if dest_ip_obj and router_networks:
            for network_info in router_networks:
                if dest_ip_obj in network_info['network']:
                    dest_in_direct_network = True
                    dest_network_info = network_info
                    break
        
        if dest_in_direct_network and dest_network_info:
            if dest_node:
                if self._are_nodes_connected(router_node, dest_node):
                    return dest_node, True
                
                connected_nodes = {}
                for intf in router_node.intfList():
                    if intf.name == 'lo' or not intf.link:
                        continue
                    
                    other_end = intf.link.intf2 if intf.link.intf1 == intf else intf.link.intf1
                    other_node = other_end.node
                    
                    if came_from_node and other_node.name == came_from_node:
                        continue
                    
                    connected_nodes[other_node.name] = other_node
                
                if active_topology:
                    potential_switches = []
                    
                    for link in active_topology.links:
                        if (link['node1'] == dest_node.name and link['node2'].startswith('s')) or \
                           (link['node2'] == dest_node.name and link['node1'].startswith('s')):
                            switch_name = link['node2'] if link['node1'] == dest_node.name else link['node1']
                            
                            if switch_name in connected_nodes:
                                return connected_nodes[switch_name], False
                            else:
                                potential_switches.append(switch_name)
                    
                    if potential_switches:
                        for connected_name, connected_node in connected_nodes.items():
                            if connected_name.startswith('s'):
                                for link in active_topology.links:
                                    if (link['node1'] == connected_name and link['node2'] in potential_switches) or \
                                       (link['node2'] == connected_name and link['node1'] in potential_switches):
                                        return connected_node, False
            
            if dest_network_info and dest_network_info.get('interface'):
                for intf in router_node.intfList():
                    if intf.name == dest_network_info['interface'] and intf.link:
                        other_end = intf.link.intf2 if intf.link.intf1 == intf else intf.link.intf1
                        other_node = other_end.node
                        
                        if came_from_node and other_node.name == came_from_node:
                            continue
                        
                        return other_node, False
        
        if active_topology and hasattr(active_topology, 'routers'):
            for db_router in active_topology.routers:
                if db_router['name'] == router_node.name and 'routes' in db_router and db_router['routes']:
                    for route in db_router['routes']:
                        if 'network' in route:
                            try:
                                route_network = IPv4Network(route['network'], strict=False)
                                if dest_ip_obj and dest_ip_obj in route_network:
                                    if 'next_hop' in route and route['next_hop']:
                                        next_hop_ip = route['next_hop']
                                        next_hop_node = self.topology_manager.get_node_by_ip(next_hop_ip)
                                        if next_hop_node and (not came_from_node or next_hop_node.name != came_from_node):
                                            return next_hop_node, False
                                            
                                    elif 'interface' in route and route['interface']:
                                        interface_name = route['interface']
                                        for intf in router_node.intfList():
                                            if intf.name == interface_name and intf.link:
                                                other_intf = intf.link.intf1 if intf.link.intf2 == intf else intf.link.intf2
                                                other_node = other_intf.node
                                                if not came_from_node or other_node.name != came_from_node:
                                                    return other_node, False
                            except Exception as e:
                                pass
        
        dest_network = None
        try:
            dest_network = IPv4Network(f"{dest_ip}/24", strict=False)
        except Exception as e:
            pass
        
        if dest_network and router_networks:
            for network_info in router_networks:
                router_network = network_info['network']
                if dest_network.overlaps(router_network):
                    if network_info.get('interface'):
                        for intf in router_node.intfList():
                            if intf.name == network_info['interface'] and intf.link:
                                other_intf = intf.link.intf1 if intf.link.intf2 == intf else intf.link.intf2
                                other_node = other_intf.node
                                if not came_from_node or other_node.name != came_from_node:
                                    return other_node, False
        
        connected_hosts = []
        connected_switches = []
        connected_routers = []
        
        for intf in router_node.intfList():
            if intf.name == 'lo' or not intf.link:
                continue
                
            other_intf = intf.link.intf1 if intf.link.intf2 == intf else intf.link.intf2
            other_node = other_intf.node
            
            if came_from_node and other_node.name == came_from_node:
                continue
            
            if other_node.name.startswith('s') and active_topology:
                for link in active_topology.links:
                    if (dest_node and link['node1'] == dest_node.name and link['node2'] == other_node.name) or \
                       (dest_node and link['node2'] == dest_node.name and link['node1'] == other_node.name):
                        return other_node, False
            
            if other_node.name.startswith('h'):
                connected_hosts.append(other_node)
            elif other_node.name.startswith('s'):
                connected_switches.append(other_node)
            elif other_node.name.startswith('r'):
                if other_node.name != router_node.name:
                    connected_routers.append(other_node)
        
        if connected_switches:
            next_node = connected_switches[0]
            return next_node, False
            
        if connected_hosts:
            next_node = connected_hosts[0]
            return next_node, False
            
        if connected_routers:
            next_node = connected_routers[0]
            return next_node, False
        
        return None, False

    def stop_trace(self, trace_id):
        """Остановка трассировки"""
        if trace_id in self.traces:
            self.complete_trace(trace_id, success=False, error="Trace stopped by user")
            return True
        return False

    def trace_with_scapy(self, trace_id, source, destination, packet_config):
        """Трассировка маршрута с использованием встроенной функции traceroute Scapy"""
        try:
            source_node = self.topology_manager.get_node(source)
            dest_node = self.topology_manager.get_node(destination)
            
            if not source_node or not dest_node:
                raise Exception(f"Source or destination node not found: {source if not source_node else ''} {destination if not dest_node else ''}")
                
            source_ip = self._get_node_ip(source_node)
            if not source_ip:
                raise Exception(f"Source node {source} has no IP address")
            source_ip = source_ip.split('/')[0]
            
            dest_ip = self._get_node_ip(dest_node)
            if not dest_ip:
                raise Exception(f"Destination node {destination} has no IP address")
            dest_ip = dest_ip.split('/')[0]
            
            self.traces[trace_id] = {
                "source": source,
                "destination": destination,
                "source_ip": source_ip,
                "destination_ip": dest_ip,
                "current_node": source,
                "hops": [{
                    "node": source,
                    "time": time.time(),
                    "action": "start",
                    "details": f"Starting Scapy traceroute from {source_ip} to {dest_ip}"
                }],
                "state": "in_progress",
                "error": None
            }
            
            protocol = packet_config.get('protocol', 'icmp').lower()
            max_ttl = packet_config.get('max_ttl', 20)
            timeout = packet_config.get('timeout', 2)
            verbose = packet_config.get('verbose', 0)
            
            if protocol == 'tcp':
                dport = packet_config.get('dport', 80)
                packet = IP(dst=dest_ip)/TCP(dport=dport)
            elif protocol == 'udp':
                dport = packet_config.get('dport', 53)
                packet = IP(dst=dest_ip)/UDP(dport=dport)
            else:
                packet = IP(dst=dest_ip)/ICMP()
                
            trace_cmd = (
                f"from scapy.all import *; "
                f"result, _ = traceroute('{dest_ip}', maxttl={max_ttl}, timeout={timeout}, verbose={verbose})"
            )
            
            if protocol != 'icmp':
                if protocol == 'tcp':
                    trace_cmd = (
                        f"from scapy.all import *; "
                        f"p = IP(dst='{dest_ip}')/TCP(dport={dport}); "
                        f"result, _ = traceroute(target='{dest_ip}', maxttl={max_ttl}, timeout={timeout}, verbose={verbose}, l4=TCP(dport={dport}))"
                    )
                elif protocol == 'udp':
                    trace_cmd = (
                        f"from scapy.all import *; "
                        f"p = IP(dst='{dest_ip}')/UDP(dport={dport}); "
                        f"result, _ = traceroute(target='{dest_ip}', maxttl={max_ttl}, timeout={timeout}, verbose={verbose}, l4=UDP(dport={dport}))"
                    )
            
            cmd = f'python3 -c "{trace_cmd}"'
            
            try:
                output = source_node.cmd(cmd)
                
                lines = output.strip().split('\n')
                current_hop = 1
                
                for line in lines:
                    if not line or line.startswith('traceroute') or line.startswith('Starting'):
                        continue
                        
                    try:
                        if ' ' in line:
                            parts = line.split()
                            hop_ip = None
                            hop_time = None
                            
                            for part in parts:
                                if part.count('.') == 3 and all(p.isdigit() for p in part.split('.')):
                                    hop_ip = part
                                    break
                                    
                            for i, part in enumerate(parts):
                                if part.endswith('ms') and i > 0:
                                    try:
                                        hop_time = float(parts[i-1])
                                    except:
                                        pass
                            
                            if hop_ip:
                                hop_node = self.topology_manager.get_node_by_ip(hop_ip)
                                node_name = hop_node.name if hop_node else f"unknown-{hop_ip}"
                                
                                self.add_hop(trace_id, node_name, "hop", 
                                    f"TTL={current_hop} IP={hop_ip}" + 
                                    (f" time={hop_time}ms" if hop_time else "")
                                )
                                
                                if hop_ip == dest_ip:
                                    self.add_hop(trace_id, node_name, "receive", 
                                        f"Packet reached destination {dest_ip}")
                                    break
                                    
                                current_hop += 1
                            elif '*' in line:
                                self.add_hop(trace_id, f"hop-{current_hop}", "timeout", 
                                    f"No response (TTL={current_hop})")
                                current_hop += 1
                    except Exception as parse_error:
                        pass
                
                self.complete_trace(trace_id, success=True)
                return self.get_trace_info(trace_id)
                
            except Exception as cmd_error:
                error_msg = f"Error executing traceroute: {str(cmd_error)}"
                self.complete_trace(trace_id, success=False, error=error_msg)
                return self.get_trace_info(trace_id)
                
        except Exception as e:
            error_msg = f"Error in Scapy traceroute: {str(e)}"
            if trace_id in self.traces:
                self.complete_trace(trace_id, success=False, error=error_msg)
            return {"error": error_msg}
            
    def traceroute(self, source_node_name, destination_ip, config=None):
        """Выполняет трассировку маршрута от источника к IP-адресу назначения"""
        if config is None:
            config = {}
            
        trace_id = f"traceroute-{time.time()}"
        
        dest_node = self.topology_manager.get_node_by_ip(destination_ip)
        if not dest_node:
            for node_name, node in self.topology_manager.nodes.items():
                node_ip = self._get_node_ip(node)
                if node_ip and node_ip.split('/')[0] == destination_ip:
                    dest_node = node
                    break
                    
        if not dest_node:
            return {
                "success": False,
                "error": f"No host with IP {destination_ip} found"
            }
            
        if 'protocol' not in config:
            config['protocol'] = 'icmp'
            
        result = self.trace_with_scapy(trace_id, source_node_name, dest_node.name, config)
        
        formatted_result = {
            "source": source_node_name,
            "destination": dest_node.name,
            "destination_ip": destination_ip,
            "success": result.get("success", False) if isinstance(result, dict) else False,
            "hops": result.get("hops", []) if isinstance(result, dict) else [],
            "error": result.get("error") if isinstance(result, dict) else str(result)
        }
        
        return formatted_result