from ipaddress import IPv4Network, IPv4Address, IPv4Interface
from typing import List, Dict, Any, Tuple, Set, Optional
import logging

logger = logging.getLogger(__name__)

class TopologyValidator:
    """
    Проверяет сетевые топологии на корректность в соответствии с принципами сетей.
    Использует объекты топологии mininet и scapy для проверки.
    """

    def __init__(self, topology_manager):
        """
        Инициализирует валидатор со ссылкой на менеджер топологии.
        
        Аргументы:
            topology_manager: Менеджер топологии, содержащий сеть для проверки
        """
        self.topology_manager = topology_manager
        
    def validate_topology(self) -> Dict[str, Any]:
        """
        Проверяет текущую топологию на корректность.
        
        Возвращает:
            Словарь, содержащий результаты проверки с ошибками и предупреждениями
        """
        if not self.topology_manager.is_running():
            return {
                "valid": False,
                "errors": ["Сеть не запущена. Пожалуйста, сначала активируйте топологию."],
                "warnings": []
            }
            
        try:
            result = {
                "valid": True,
                "errors": [],
                "warnings": []
            }
            
            self._validate_ip_addressing(result)
            self._validate_connectivity(result)
            self._validate_loops(result)
            self._validate_subnets(result)
            self._validate_routers(result)
            
            result["valid"] = len(result["errors"]) == 0
            
            return result
        except Exception as e:
            logger.exception("Error during topology validation")
            return {
                "valid": False,
                "errors": [f"Ошибка проверки: {str(e)}"],
                "warnings": []
            }
    
    def _validate_ip_addressing(self, result: Dict[str, Any]):
        """
        Проверяет IP-адресацию в сети:
        - Хосты должны иметь действительные IP-адреса
        - Не должно быть дублирующихся IP-адресов
        - IP-адреса должны иметь правильный формат
        
        Аргументы:
            result: Словарь результатов проверки для обновления
        """
        if not self.topology_manager.net:
            result["errors"].append("Сеть не инициализирована")
            return
            
        all_hosts = self.topology_manager.net.hosts
        routers = [node for node in all_hosts if node.name.startswith('r')]
        
        hosts = [node for node in all_hosts if not node.name.startswith('r')]
        
        print(f"Processing {len(hosts)} hosts and {len(routers)} routers")
        ip_addresses = {}
        
        active_topology = None
        if hasattr(self.topology_manager, 'active_topology'):
            active_topology = self.topology_manager.active_topology
        
        for host in hosts:
            host_ip = None
            for intf in host.intfList():
                print(f"Host {host.name} interface: {intf.name}, ip: {intf.ip}")
                if intf.name != 'lo' and intf.ip:
                    host_ip = intf.ip
                    break
            
            if (not host_ip or host_ip == '0.0.0.0') and active_topology:
                for db_host in active_topology.hosts:
                    if db_host['name'] == host.name and 'ip' in db_host and db_host['ip']:
                        host_ip = db_host['ip'].split('/')[0] if '/' in db_host['ip'] else db_host['ip']
                        print(f"Found IP {host_ip} for host {host.name} in database")
                        break
            
            if not host_ip or host_ip == '0.0.0.0':
                print(f"Host {host.name} has no valid IP: {host_ip}, interfaces: {[intf.name for intf in host.intfList()]}")
                result["errors"].append(f"Хост {host.name} не имеет действительного IP-адреса")
                continue
                
            try:
                IPv4Address(host_ip)
                
                if host_ip in ip_addresses:
                    result["errors"].append(
                        f"Дублирующийся IP-адрес {host_ip} на хостах {host.name} и {ip_addresses[host_ip]}"
                    )
                else:
                    ip_addresses[host_ip] = host.name
            except ValueError:
                result["errors"].append(f"Неверный формат IP-адреса {host_ip} на хосте {host.name}")
        
        for router in routers:
            router_has_valid_ip = False
            
            for intf in router.intfList():
                print(f"Router {router.name} interface: {intf.name}, ip: {intf.ip}")
                if intf.name == 'lo' or not intf.link:
                    continue
                
                try:
                    router.cmd(f'ip link set {intf.name} up')
                    
                    ip_result = router.cmd(f"ip -o -4 addr show dev {intf.name} | awk '{{print $4}}'").strip()
                    print(f"IP command result for {router.name} interface {intf.name}: '{ip_result}'")
                    
                    if ip_result and ip_result != '':
                        if '/' in ip_result:
                            router_ip = ip_result.split('/')[0]
                        else:
                            router_ip = ip_result
                            
                        if router_ip and router_ip != '0.0.0.0':
                            router_has_valid_ip = True
                            print(f"Found valid IP {router_ip} on {router.name} interface {intf.name}")
                            
                            try:
                                IPv4Address(router_ip)
                                
                                if router_ip in ip_addresses:
                                    result["errors"].append(
                                        f"Дублирующийся IP-адрес {router_ip} на маршрутизаторе {router.name} и {ip_addresses[router_ip]}"
                                    )
                                else:
                                    ip_addresses[router_ip] = f"{router.name}:{intf.name}"
                            except ValueError:
                                result["errors"].append(f"Неверный формат IP-адреса {router_ip} на интерфейсе {intf.name} маршрутизатора {router.name}")
                except Exception as e:
                    print(f"Error checking IP for {router.name} interface {intf.name}: {str(e)}")
            
            if not router_has_valid_ip and active_topology and hasattr(active_topology, 'routers'):
                for db_router in active_topology.routers:
                    if db_router['name'] == router.name:
                        if 'ip' in db_router and db_router['ip']:
                            router_ip = db_router['ip'].split('/')[0] if '/' in db_router['ip'] else db_router['ip']
                            router_has_valid_ip = True
                            print(f"Found IP {router_ip} for router {router.name} in database")
                        
                        if 'interfaces' in db_router and db_router['interfaces']:
                            for intf in db_router['interfaces']:
                                if 'ip' in intf and intf['ip']:
                                    router_ip = intf['ip'].split('/')[0] if '/' in intf['ip'] else intf['ip']
                                    router_has_valid_ip = True
                                    print(f"Found interface IP {router_ip} for router {router.name} in database")
                        break
            
            if not router_has_valid_ip:
                print(f"Router {router.name} has no valid IPs, interfaces: {[intf.name for intf in router.intfList()]}")
                result["errors"].append(f"Роутер {router.name} не имеет ни одного действительного IP-адреса")
    
    def _validate_connectivity(self, result: Dict[str, Any]):
        """
        Проверяет правильность подключений в сети:
        - Каждый хост должен быть подключен хотя бы к одному коммутатору или маршрутизатору
        - Не должно быть прямых подключений хост-к-хосту
        - Коммутаторы не должны напрямую соединяться с другими подсетями (должны проходить через маршрутизаторы)
        
        Аргументы:
            result: Словарь результатов проверки для обновления
        """
        if not self.topology_manager.net:
            return
            
        all_nodes = self.topology_manager.net.hosts
        routers = [node for node in all_nodes if node.name.startswith('r')]
        hosts = [node for node in all_nodes if not node.name.startswith('r')]
        switches = self.topology_manager.net.switches
        
        for host in hosts:
            connected_to_switch_or_router = False
            direct_host_connections = []
            
            for intf in host.intfList():
                if intf.name == 'lo' or not intf.link:
                    continue
                    
                other_intf = intf.link.intf1 if intf.link.intf2 == intf else intf.link.intf2
                other_node = other_intf.node
                
                if other_node in switches or other_node in routers:
                    connected_to_switch_or_router = True
                elif other_node in hosts:
                    direct_host_connections.append(other_node.name)
            
            if not connected_to_switch_or_router:
                result["errors"].append(f"Хост {host.name} не подключен ни к одному коммутатору или маршрутизатору")
                
            if direct_host_connections:
                result["errors"].append(
                    f"Хост {host.name} напрямую подключен к другим хостам: {', '.join(direct_host_connections)}"
                )
    
    def _validate_loops(self, result: Dict[str, Any]):
        """
        Проверяет отсутствие петель в топологии коммутаторов
        (если STP не реализован, что в настоящее время не поддерживается)
        
        Аргументы:
            result: Словарь результатов проверки для обновления
        """
        if not self.topology_manager.net:
            return
            
        switches = self.topology_manager.net.switches
        
        switch_connections = {switch.name: set() for switch in switches}
        
        for switch in switches:
            for intf in switch.intfList():
                if intf.name == 'lo' or not intf.link:
                    continue
                
                other_intf = intf.link.intf1 if intf.link.intf2 == intf else intf.link.intf2
                other_node = other_intf.node
                
                if other_node in switches:
                    switch_connections[switch.name].add(other_node.name)
        
        visited = set()
        path = set()
        
        def has_cycle(node, parent=None):
            """Поиск в глубину для обнаружения циклов"""
            visited.add(node)
            path.add(node)
            
            for neighbor in switch_connections[node]:
                if neighbor == parent:
                    continue
                
                if neighbor in path:
                    return True
                
                if neighbor not in visited:
                    if has_cycle(neighbor, node):
                        return True
            
            path.remove(node)
            return False
        
        cycles_found = False
        for switch_name in switch_connections:
            if switch_name not in visited:
                if has_cycle(switch_name):
                    cycles_found = True
                    break
        
        if cycles_found:
            result["errors"].append(
                "Топология содержит петли коммутаторов, которые могут вызвать широковещательные штормы. Добавьте STP для управления петлями или удалите их."
            )

    def _validate_subnets(self, result: Dict[str, Any]):
        """
        Проверяет конфигурацию подсетей:
        - Хосты, подключенные к одному коммутатору, должны быть в одной подсети
        - Проверяет, что подсети не перекрываются некорректно
        - Каждая подсеть должна быть доступна через маршрутизатор
        
        Аргументы:
            result: Словарь результатов проверки для обновления
        """
        if not self.topology_manager.net:
            return
            
        switch_subnets = {}
        
        all_nodes = self.topology_manager.net.hosts
        routers = [node for node in all_nodes if node.name.startswith('r')]
        hosts = [node for node in all_nodes if not node.name.startswith('r')]
        switches = self.topology_manager.net.switches
        
        active_topology = None
        if hasattr(self.topology_manager, 'active_topology'):
            active_topology = self.topology_manager.active_topology
        
        host_subnets = {}
        for host in hosts:
            host_ip = None
            host_mask = None
            
            for intf in host.intfList():
                if intf.name != 'lo' and intf.ip:
                    host_ip = intf.ip
                    host_mask = intf.prefixLen if hasattr(intf, 'prefixLen') else 24
                    break
            
            if (not host_ip or host_ip == '0.0.0.0') and active_topology:
                for db_host in active_topology.hosts:
                    if db_host['name'] == host.name and 'ip' in db_host and db_host['ip']:
                        db_ip = db_host['ip']
                        if '/' in db_ip:
                            host_ip, mask_str = db_ip.split('/')
                            host_mask = int(mask_str)
                        else:
                            host_ip = db_ip
                            host_mask = 24
                        print(f"Found IP {host_ip}{host_mask} for host {host.name} in database")
                        break
            
            if not host_ip or host_ip == '0.0.0.0':
                continue
                
            try:
                subnet = IPv4Network(f"{host_ip}{host_mask}", strict=False)
                host_subnets[host.name] = subnet
            except ValueError:
                result["errors"].append(f"Неверная подсеть для хоста {host.name}: {host_ip}{host_mask}")
        
        router_subnets = {}
        all_router_interfaces = set()
        for router in routers:
            router_subnets[router.name] = []
            
            for intf in router.intfList():
                if intf.name == 'lo' or not intf.link:
                    continue
                    
                try:
                    router.cmd(f'ip link set {intf.name} up')
                    
                    ip_result = router.cmd(f"ip -o -4 addr show dev {intf.name} | awk '{{print $4}}'").strip()
                    if not ip_result or ip_result == '':
                        continue
                        
                    if '/' in ip_result:
                        router_ip, mask_str = ip_result.split('/')
                        mask = int(mask_str)
                    else:
                        router_ip = ip_result
                        mask = 24
                        
                    if router_ip and router_ip != '0.0.0.0':
                        try:
                            subnet = IPv4Network(f"{router_ip}/{mask}", strict=False)
                            router_subnets[router.name].append((subnet, intf.name))
                            all_router_interfaces.add((router.name, router_ip, str(subnet), intf.name))
                            print(f"Found subnet {subnet} on {router.name} interface {intf.name}")
                        except ValueError:
                            result["errors"].append(f"Неверная подсеть для интерфейса {intf.name} маршрутизатора {router.name}: {router_ip}/{mask}")
                except Exception as e:
                    print(f"Error checking subnet for {router.name} interface {intf.name}: {str(e)}")
            
            if active_topology and hasattr(active_topology, 'routers'):
                for db_router in active_topology.routers:
                    if db_router['name'] == router.name and 'interfaces' in db_router and db_router['interfaces']:
                        for intf in db_router['interfaces']:
                            if 'name' in intf and 'ip' in intf and intf['ip']:
                                intf_name = intf['name']
                                ip_str = intf['ip']
                                
                                if '/' in ip_str:
                                    router_ip, mask_str = ip_str.split('/')
                                    mask = int(mask_str)
                                else:
                                    router_ip = ip_str
                                    mask = intf.get('subnet_mask', 24)
                                
                                try:
                                    subnet = IPv4Network(f"{router_ip}/{mask}", strict=False)
                                    intf_exists = False
                                    for existing_router, existing_ip, existing_subnet, existing_name in all_router_interfaces:
                                        if existing_router == router.name and existing_name == intf_name:
                                            intf_exists = True
                                            break
                                    
                                    if not intf_exists:
                                        router_subnets[router.name].append((subnet, intf_name))
                                        all_router_interfaces.add((router.name, router_ip, str(subnet), intf_name))
                                        print(f"Found subnet {subnet} on {router.name} interface {intf_name} in database")
                                except ValueError:
                                    result["errors"].append(f"Неверная подсеть для интерфейса {intf_name} маршрутизатора {router.name} из БД: {router_ip}/{mask}")
        
        for host in hosts:
            if host.name not in host_subnets:
                continue
                
            host_subnet = host_subnets[host.name]
            
            for intf in host.intfList():
                if intf.name == 'lo' or not intf.link:
                    continue
                
                other_intf = intf.link.intf1 if intf.link.intf2 == intf else intf.link.intf2
                other_node = other_intf.node
                
                if other_node in switches:
                    switch_name = other_node.name
                    if switch_name not in switch_subnets:
                        switch_subnets[switch_name] = set()
                    
                    switch_subnets[switch_name].add(host_subnet)
        
        for switch_name, subnets in switch_subnets.items():
            if len(subnets) > 1:
                result["warnings"].append(
                    f"Коммутатор {switch_name} имеет хосты в разных подсетях: {[str(s) for s in subnets]}"
                )
        
        all_subnets = set()
        for subnets in switch_subnets.values():
            all_subnets.update(subnets)
            
        for subnet in all_subnets:
            subnet_has_router = False
            subnet_str = str(subnet)
            connected_interfaces = []
            
            for router_name, router_ip, router_subnet_str, intf_name in all_router_interfaces:
                router_subnet = IPv4Network(router_subnet_str)
                if subnet == router_subnet or subnet.overlaps(router_subnet):
                    subnet_has_router = True
                    connected_interfaces.append(f"{router_name}:{intf_name}({router_ip})")
            
            if not subnet_has_router:
                result["errors"].append(
                    f"Подсеть {subnet} не подключена ни к одному маршрутизатору и не будет доступна из других подсетей"
                )
            else:
                print(f"Subnet {subnet} connected via router interfaces: {', '.join(connected_interfaces)}")
    
    def _validate_routers(self, result: Dict[str, Any]):
        """
        Проверяет конфигурацию маршрутизаторов:
        - Маршрутизаторы должны иметь как минимум 2 интерфейса с IP в разных подсетях
        - У маршрутизаторов должна быть включена переадресация
        - Проверка маршрутов по умолчанию
        
        Аргументы:
            result: Словарь результатов проверки для обновления
        """
        if not self.topology_manager.net:
            return
            
        all_nodes = self.topology_manager.net.hosts
        routers = [node for node in all_nodes if node.name.startswith('r')]
        
        active_topology = None
        if hasattr(self.topology_manager, 'active_topology'):
            active_topology = self.topology_manager.active_topology
        
        print(f"Validating {len(routers)} routers")
        
        for router in routers:
            ips_by_subnet = {}
            
            for intf in router.intfList():
                if intf.name == 'lo' or not intf.link:
                    continue
                
                try:
                    router.cmd(f'ip link set {intf.name} up')
                    
                    ip_result = router.cmd(f"ip -o -4 addr show dev {intf.name} | awk '{{print $4}}'").strip()
                    print(f"Router {router.name} interface {intf.name} IP result: '{ip_result}'")
                    
                    if not ip_result or ip_result == '':
                        continue
                        
                    if '/' in ip_result:
                        router_ip, mask_str = ip_result.split('/')
                        mask = int(mask_str)
                    else:
                        router_ip = ip_result
                        mask = 24
                        
                    if router_ip and router_ip != '0.0.0.0':
                        try:
                            subnet = IPv4Network(f"{router_ip}{mask}", strict=False)
                            subnet_str = str(subnet)
                            
                            if subnet_str not in ips_by_subnet:
                                ips_by_subnet[subnet_str] = []
                            
                            ips_by_subnet[subnet_str].append((router_ip, intf.name))
                            print(f"Found subnet {subnet} with IP {router_ip} on {router.name} interface {intf.name}")
                        except ValueError:
                            continue
                except Exception as e:
                    print(f"Error checking subnet for {router.name} interface {intf.name}: {str(e)}")
            
            if active_topology and hasattr(active_topology, 'routers'):
                for db_router in active_topology.routers:
                    if db_router['name'] == router.name and 'interfaces' in db_router and db_router['interfaces']:
                        for intf in db_router['interfaces']:
                            if 'name' in intf and 'ip' in intf and intf['ip']:
                                intf_name = intf['name']
                                ip_str = intf['ip']
                                
                                if '/' in ip_str:
                                    router_ip, mask_str = ip_str.split('/')
                                    mask = int(mask_str)
                                else:
                                    router_ip = ip_str
                                    mask = intf.get('subnet_mask', 24)
                                
                                try:
                                    subnet = IPv4Network(f"{router_ip}{mask}", strict=False)
                                    subnet_str = str(subnet)
                                    
                                    if subnet_str not in ips_by_subnet:
                                        ips_by_subnet[subnet_str] = []
                                    
                                    interface_exists = False
                                    for existing_ip, existing_name in ips_by_subnet[subnet_str]:
                                        if existing_name == intf_name:
                                            interface_exists = True
                                            break
                                    
                                    if not interface_exists:
                                        ips_by_subnet[subnet_str].append((router_ip, intf_name))
                                        print(f"Found subnet {subnet} with IP {router_ip} on {router.name} interface {intf_name} from database")
                                except ValueError:
                                    continue
            
            for subnet, ips in ips_by_subnet.items():
                if len(ips) > 1:
                    result["warnings"].append(
                        f"Роутер {router.name} имеет несколько одинаковых IP-адресов в одной подсети {subnet}: {[ip[0] for ip in ips]}"
                    ) 