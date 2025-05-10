from mininet.net import Mininet
from mininet.node import Controller, OVSSwitch, NOX
from mininet.topo import Topo
import time
from ipaddress import IPv4Network, IPv4Address
import random
import os
import subprocess

class NetworkTopology:
    def __init__(self):
        self.net = None
        self.topo = None
        self.nodes = {}
        self.ip_pool = list(IPv4Network('10.0.0.0/24').hosts())
        self.used_ips = set()
        self.switch_ip_map = {}
        self.active_topology = None
        
    def is_running(self):
        """Проверка, инициализирована ли сеть и запущена ли"""
        return self.net is not None
        
    def get_next_ip(self):
        """Получение следующего доступного IP-адреса"""
        available_ips = [ip for ip in self.ip_pool if ip not in self.used_ips]
        if not available_ips:
            raise Exception("Нет доступных IP-адресов")
        
        ip = random.choice(available_ips)
        self.used_ips.add(ip)
        return f"{ip}/24"

    def assign_ip_to_switch(self, switch_name, ip=None):
        """Присваивание IP-адреса к коммутатору (управление IP)"""
        if not ip:
            ip = self.get_next_ip()
        
        self.switch_ip_map[switch_name] = ip
        return ip

    def get_switch_ip(self, switch_name):
        """Получение управляющего IP-адреса коммутатора"""
        return self.switch_ip_map.get(switch_name)

    def ensure_ovs_running(self):
        """Удостовериться, что OVS запущен"""
        import subprocess
        import time
        import os
        
        print("Checking Open vSwitch status...")
        
        try:
            result = subprocess.run(['ovs-vsctl', 'show'], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE, 
                                   text=True, 
                                   check=False)
            
            if result.returncode == 0:
                print("Open vSwitch is running")
                return True
        except Exception as e:
            print(f"Error checking OVS status: {str(e)}")
        
        print("Open vSwitch is not running. Attempting to start services...")
        
        try:
            print("Trying to start OVS via service command...")
            subprocess.run(['service', 'openvswitch-switch', 'start'], 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE)
            
            print("Trying to start OVS via systemctl...")
            subprocess.run(['systemctl', 'start', 'openvswitch-switch'], 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE)
            
            print("Trying direct OVS initialization...")
            os.makedirs('/var/run/openvswitch', exist_ok=True)
            os.makedirs('/etc/openvswitch', exist_ok=True)
                
            subprocess.run(['ovsdb-tool', 'create', '/etc/openvswitch/conf.db', 
                           '/usr/share/openvswitch/vswitch.ovsschema'],
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE)
            
            subprocess.Popen(['ovsdb-server', '--remote=punix:/var/run/openvswitch/db.sock',
                             '--remote=db:Open_vSwitch,Open_vSwitch,manager_options',
                             '--pidfile', '--detach'])
            
            subprocess.Popen(['ovs-vswitchd', '--pidfile', '--detach'])
            
            print("Waiting for OVS services to start...")
            time.sleep(3)
            
            result = subprocess.run(['ovs-vsctl', 'show'], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE, 
                                   text=True, 
                                   check=False)
            
            if result.returncode == 0:
                print("Successfully started Open vSwitch services")
                return True
            else:
                print("Failed to start Open vSwitch services")
                print(f"Output: {result.stdout}")
                print(f"Error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Error starting OVS services: {str(e)}")
            return False

    def create_network(self, config):
        """Создание новой топологии сети"""
        print("Создание сети с конфигурацией:", config)
        
        self.ensure_ovs_running()
        
        if self.net:
            print("Stopping existing network")
            try:
                self.stop_network()
                print("Existing network stopped successfully")
            except Exception as e:
                print(f"Warning: Error stopping existing network: {str(e)}")

        print("Creating new topology")
        self.topo = Topo()
        self.nodes = {}
        self.used_ips = set()

        print("Creating Mininet instance")
        try:
            try:
                self.net = Mininet(
                    topo=self.topo,
                    switch=OVSSwitch,
                    controller=None,
                    autoSetMacs=True,
                    waitConnected=False,
                    ipBase='10.0.0.0/24',
                    cleanup=True
                )
                print(f"Mininet instance created: {self.net}")
            except Exception as mininet_error:
                print(f"Exception during Mininet creation: {str(mininet_error)}")
                print(f"Exception type: {type(mininet_error)}")
                raise

            if not hasattr(self.net, 'start'):
                raise Exception("Failed to create valid Mininet instance")
                
            print("Starting Mininet")
            try:
                print(f"Current network state before start: {self.net}")
                if hasattr(self.net, 'controllers'):
                    print(f"Controllers: {self.net.controllers}")
                if hasattr(self.net, 'topo'):
                    print(f"Topology: {self.net.topo}")
                
                self.net.start()
                print("Mininet start() method completed")
                
                if hasattr(self.net, 'switches'):
                    print(f"Network has {len(self.net.switches)} switches after start")
                if hasattr(self.net, 'hosts'):
                    print(f"Network has {len(self.net.hosts)} hosts after start")
            except Exception as start_error:
                print(f"Exception during Mininet start: {str(start_error)}")
                import traceback
                traceback.print_exc()
                raise
                
            time.sleep(2)
            print("Mininet started successfully")

            print("Adding hosts...")
            added_hosts = set()
            for host_config in config.get('hosts', []):
                name = host_config['name']
                if name not in added_hosts:
                    try:
                        ip = host_config.get('ip') or self.get_next_ip()
                        host = self.net.addHost(name, ip=ip)
                        self.nodes[name] = host
                        added_hosts.add(name)
                        print(f"Added host: {name} with IP {ip}")
                    except Exception as e:
                        print(f"Error adding host {name}: {str(e)}")
                        raise

            print("Adding switches...")
            for switch_config in config.get('switches', []):
                try:
                    switch = self.net.addSwitch(switch_config['name'])
                    self.nodes[switch_config['name']] = switch
                    print(f"Added switch: {switch_config['name']}")
                except Exception as e:
                    print(f"Error adding switch {switch_config['name']}: {str(e)}")
                    raise
                
            print("Adding router nodes...")
            for router_config in config.get('routers', []):
                try:
                    router = self.add_router(router_config['name'])
                    self.nodes[router_config['name']] = router
                    print(f"Added router node: {router_config['name']}")
                except Exception as e:
                    print(f"Error adding router node {router_config['name']}: {str(e)}")
                    raise

            print("Adding links...")
            for link in config.get('links', []):
                try:
                    n1 = self.nodes.get(link['node1'])
                    n2 = self.nodes.get(link['node2'])
                    if n1 and n2:
                        self.net.addLink(n1, n2)
                        print(f"Added link: {link['node1']} <-> {link['node2']}")
                except Exception as e:
                    print(f"Error adding link {link['node1']} <-> {link['node2']}: {str(e)}")
                    raise
                    
            print("Configuring routers...")
            for router_config in config.get('routers', []):
                try:
                    router_name = router_config['name']
                    print(f"Configuring router: {router_name}")
                    
                    if 'interfaces' in router_config:
                        for intf_config in router_config['interfaces']:
                            if 'name' in intf_config and 'ip' in intf_config:
                                try:
                                    self.configure_router_interface(
                                        router_name,
                                        intf_config['name'],
                                        intf_config['ip'],
                                        intf_config.get('subnet_mask', 24)
                                    )
                                except Exception as e:
                                    print(f"Error configuring router interface: {str(e)}")
                    
                    if 'routes' in router_config:
                        for route_config in router_config['routes']:
                            if 'network' in route_config:
                                try:
                                    self.add_route(
                                        router_name,
                                        route_config['network'],
                                        route_config.get('next_hop'),
                                        route_config.get('interface')
                                    )
                                except Exception as e:
                                    print(f"Error adding route to router: {str(e)}")
                                
                    print(f"Router {router_name} configured successfully")
                except Exception as e:
                    print(f"Error configuring router {router_config['name']}: {str(e)}")

            if not hasattr(self.net, 'switches'):
                print("WARNING: Network object missing 'switches' attribute")
            else:
                print(f"Network has {len(self.net.switches)} switches")
                
            if not hasattr(self.net, 'hosts'):
                print("WARNING: Network object missing 'hosts' attribute")
            else:
                print(f"Network has {len(self.net.hosts)} hosts")
                
            if hasattr(self.net, 'built'):
                print(f"Network built property: {self.net.built}")
                if not self.net.built:
                    print("Setting network.built = True")
                    self.net.built = True
            else:
                print("WARNING: Network object missing 'built' attribute")
                try:
                    self.net.built = True
                    print("Added built=True property to network")
                except Exception as e:
                    print(f"Error adding built property: {e}")
            
            print("Configuring switches...")
            for switch in self.net.switches:
                try:
                    self.configure_switch(switch.name)
                except Exception as e:
                    print(f"Error configuring switch {switch}: {str(e)}")
                    raise
                
            for node_name, node in self.nodes.items():
                if node_name.startswith('r'):
                    try:
                        node.cmd('sysctl -w net.ipv4.ip_forward=1')
                        print(f"Enabled IP forwarding on router {node_name}")
                    except Exception as e:
                        print(f"Error enabling IP forwarding on router {node_name}: {str(e)}")

            print("Network creation completed successfully")
            return True

        except Exception as e:
            print(f"Error creating network: {str(e)}")
            if self.net:
                try:
                    self.net.stop()
                except Exception as stop_error:
                    print(f"Error stopping network during cleanup: {str(stop_error)}")
                self.net = None
            self.nodes = {}
            raise

    def stop_network(self):
        """Остановка текущей сети"""
        if self.net:
            try:
                print("Инициируем остановку сети...")
                try:
                    for switch in self.net.switches:
                        try:
                            print(f"Removing flows from switch {switch.name}")
                            os.system(f'ovs-ofctl del-flows {switch.name}')
                        except Exception as e:
                            print(f"Error removing flows from switch {switch.name}: {str(e)}")
                except Exception as sw_error:
                    print(f"Error cleaning up switches: {str(sw_error)}")
                
                print("Stopping mininet network...")
                self.net.stop()
                print("Network stopped successfully")
            except Exception as e:
                print(f"Error during network shutdown: {str(e)}")
                try:
                    print("Trying fallback cleanup...")
                    os.system('mn -c')
                    os.system('pkill -9 -f mininet')
                    os.system('pkill -9 -f ovs')
                except Exception as fallback_error:
                    print(f"Fallback cleanup also failed: {str(fallback_error)}")
            finally:
                self.net = None
                self.topo = None
                self.nodes = {}
                self.used_ips = set()
                print("Internal network state reset")

    def configure_switch(self, switch):
        """Настройка коммутатора"""
        try:
            print(f"Configuring switch {switch}")
            os.system(f'ovs-vsctl set-fail-mode {switch} standalone')
            os.system(f'ovs-vsctl set bridge {switch} stp_enable=true')
            os.system(f'ovs-ofctl add-flow {switch} action=normal')
            print(f"Switch {switch} configured successfully")
        except Exception as e:
            print(f"Error configuring switch {switch}: {str(e)}")
            raise

    def add_host(self, name, ip=None):
        """Добавление хоста в сеть"""
        print(f"Пытаемся добавить хост {name} с IP {ip}")
        if not self.net:
            print(f"ERROR: Сеть не инициализирована или не построена при добавлении хоста {name}")
            raise Exception("Network not initialized")
        
        if hasattr(self.net, 'built') and not self.net.built:
            print(f"WARNING: Network exists but 'built' property is False when adding host {name}")
            try:
                print("Setting network.built = True and continuing...")
                self.net.built = True
            except Exception as e:
                print(f"Error setting built property: {e}")
        
        if not self.net.switches:
            print("ERROR: No switches available in the network")
            raise Exception("Cannot add host: No switches available in the network. Please add a switch first.")
        
        try:
            print(f"Adding host {name} to network")
            if not ip:
                ip = self.get_next_ip()
                print(f"Generated IP {ip} for host {name}")

            host = self.net.addHost(name, ip=ip)
            if not host:
                raise Exception(f"Failed to create host {name}")

            target_switch = self.net.switches[0]
            print(f"Adding link between {name} and {target_switch}")
            try:
                link = self.net.addLink(host, target_switch)
                print(f"Link created successfully between {name} and {target_switch}")
            except Exception as link_error:
                print(f"Error creating link for host {name}: {str(link_error)}")
                
            self.nodes[name] = host
            
            if not host.intfList() or len(host.intfList()) == 0:
                print(f"Warning: Host {name} has no interfaces, trying to add one")
                try:
                    intf_name = f"{name}-eth0"
                    host.cmd(f"ip link add {intf_name} type veth peer name sw-{intf_name}")
                    host.cmd(f"ip link set {intf_name} up")
                    print(f"Manually added interface {intf_name} to {name}")
                except Exception as intf_error:
                    print(f"Error manually adding interface: {str(intf_error)}")
            
            try:
                if host.intfList() and len(host.intfList()) > 0:
                    assigned_ip = host.IP()
                    if not assigned_ip or assigned_ip == '0.0.0.0':
                        print(f"Warning: IP not properly assigned to host {name}, trying to set it explicitly")
                        if '/' in ip:
                            ip_parts = ip.split('/')
                            ip_addr = ip_parts[0]
                            mask = f"/{ip_parts[1]}"
                        else:
                            ip_addr = ip
                            mask = "/24"
                        
                        try:
                            host.setIP(ip_addr, mask, intf=host.intfList()[0])
                            assigned_ip = host.IP()
                            print(f"Set IP {assigned_ip} on host {name}")
                        except Exception as ip_error:
                            print(f"Error setting IP on host: {str(ip_error)}")
                else:
                    print(f"Warning: Cannot verify IP for host {name} as it has no interfaces")
                    assigned_ip = "unknown (no interfaces)"
            except Exception as e:
                print(f"Error checking/setting IP: {str(e)}")
                assigned_ip = "unknown (error)"
            
            print(f"Host {name} added successfully with IP {assigned_ip}")
            return host
        except Exception as e:
            print(f"Error adding host {name}: {str(e)}")
            if host:
                self.nodes[name] = host
            raise

    def add_switch(self, name):
        """Добавление коммутатора в сеть"""
        print(f"Пытаемся добавить коммутатор {name}")
        
        if not self.net:
            print(f"WARNING: Network appears to be None when adding switch {name}. This is unexpected.")
            print(f"Network object: {self.net}")
            print(f"Nodes: {self.nodes}")
            print(f"Topo: {self.topo}")
        else:
            print(f"Network object exists: {self.net}")
            if hasattr(self.net, 'built'):
                print(f"Network built property: {self.net.built}")
        
        try:
            print(f"Adding switch {name} to network")
            
            if not hasattr(self.net, 'addSwitch'):
                print(f"ERROR: Network object missing addSwitch method. Available methods: {dir(self.net)[:20]}")
                raise Exception("Network object is invalid - missing addSwitch method")
            
            switch = self.net.addSwitch(name)
            if not switch:
                print(f"Warning: addSwitch returned None for {name}")
                found_switch = next((s for s in self.net.switches if s.name == name), None)
                if found_switch:
                    print(f"Switch {name} was actually created despite None return")
                    switch = found_switch
                else:
                    raise Exception(f"Switch {name} creation failed")
            
            self.nodes[name] = switch
            
            try:
                self.configure_switch(name)
            except Exception as config_error:
                print(f"Warning: Switch created but configuration failed: {str(config_error)}")
            
            print(f"Switch {name} added successfully")
            return switch
        except Exception as e:
            print(f"Error adding switch {name}: {str(e)}")
            print(f"Current network state: nodes={self.nodes}")
            if hasattr(self.net, 'switches'):
                print(f"Current switches: {[s.name for s in self.net.switches]}")
            raise

    def add_link(self, node1, node2):
        """Добавление ссылки между двумя узлами"""
        print(f"Пытаемся добавить ссылку между {node1} и {node2}")
        if not self.net:
            print(f"ERROR: Сеть не инициализирована при добавлении ссылки между {node1} и {node2}")
            raise Exception("Network not initialized")
        
        try:
            n1 = self.nodes.get(node1)
            n2 = self.nodes.get(node2)
            
            print(f"Node lookup results: node1={node1} -> {n1}, node2={node2} -> {n2}")
            print(f"Current nodes in topology: {list(self.nodes.keys())}")
            
            if not n1 or not n2:
                missing = []
                if not n1:
                    missing.append(node1)
                if not n2:
                    missing.append(node2)
                error_msg = f"One or both nodes not found: {', '.join(missing)}"
                print(f"ERROR: {error_msg}")
                raise Exception(error_msg)
            
            print(f"Creating link between {n1} and {n2}")
            
            if not hasattr(self.net, 'addLink'):
                print(f"ERROR: Network object missing addLink method")
                raise Exception("Network object is invalid - missing addLink method")
            
            try:
                link = self.net.addLink(n1, n2)
                print(f"Link created successfully between {node1} and {node2}")
                return link
            except Exception as link_error:
                print(f"ERROR: Mininet addLink method failed: {str(link_error)}")
                print(f"Exception type: {type(link_error)}")
                import traceback
                traceback.print_exc()
                raise Exception(f"Failed to create link: {str(link_error)}")
                
        except Exception as e:
            print(f"Error creating link: {str(e)}")
            raise

    def get_node(self, name):
        """Получить узел по имени"""
        return self.nodes.get(name)

    def get_nodes(self):
        """Получить все узлы в сети"""
        if not self.net:
            return []
        
        return self.net.values()

    def get_topology_info(self):
        if not self.net:
            return {"error": "No active topology"}

        hosts = [host.name for host in self.net.hosts]
        switches = [switch.name for switch in self.net.switches]

        routers = [host.name for host in self.net.hosts if host.name.startswith('r')]

        hosts = [host for host in hosts if host not in routers]
        
        return {
            "hosts": hosts,
            "switches": switches,
            "routers": routers,
            "links": [(link.intf1.node.name, link.intf2.node.name) 
                     for link in self.net.links]
        }

    def get_node_by_ip(self, ip_address: str):
        """Найти узел по его IP-адресу"""
        if not ip_address:
            return None
            
        if '/' in ip_address:
            ip_address = ip_address.split('/')[0]
        
        print(f"Looking for node with IP {ip_address}")
        
        if self.net and hasattr(self.net, 'hosts'):
            for host in self.net.hosts:
                try:
                    if hasattr(host, 'IP') and callable(host.IP):
                        node_ip = host.IP()
                        if node_ip:
                            node_ip_clean = node_ip.split('/')[0] if '/' in node_ip else node_ip
                            if node_ip_clean == ip_address:
                                print(f"Found node {host.name} with IP {node_ip} in Mininet")
                                return host
                except Exception as e:
                    print(f"Error getting IP for host {host.name}: {str(e)}")
                
        for switch_name, ip in self.switch_ip_map.items():
            switch_ip = ip.split('/')[0] if '/' in ip else ip
            if switch_ip == ip_address:
                print(f"Found switch {switch_name} with IP {ip} in switch_ip_map")
                return self.get_node(switch_name)
        
        if hasattr(self, 'active_topology') and self.active_topology:
            for db_host in self.active_topology.hosts:
                if 'ip' in db_host and db_host['ip']:
                    db_ip = db_host['ip'].split('/')[0] if '/' in db_host['ip'] else db_host['ip']
                    if db_ip == ip_address:
                        print(f"Found host {db_host['name']} with IP {db_host['ip']} in database")
                        return self.get_node(db_host['name'])
            
            if hasattr(self.active_topology, 'routers'):
                for db_router in self.active_topology.routers:
                    if 'interfaces' in db_router:
                        for interface in db_router['interfaces']:
                            if 'ip' in interface and interface['ip']:
                                interface_ip = interface['ip'].split('/')[0] if '/' in interface['ip'] else interface['ip']
                                if interface_ip == ip_address:
                                    print(f"Found router {db_router['name']} with interface IP {interface['ip']} in database")
                                    return self.get_node(db_router['name'])
        
        print(f"No node found with IP {ip_address}")
        return None

    def add_router(self, name):
        """Добавление маршрутизатора в сеть"""
        print(f"Пытаемся добавить маршрутизатор {name}")
        
        if not self.net:
            print(f"ERROR: Network not initialized when adding router {name}")
            raise Exception("Network not initialized")
        
        try:
            print(f"Adding router {name} to network")
            
            try:
                router = self.net.addHost(name)
                if not router:
                    print(f"Warning: addHost returned None for router {name}")
            except Exception as add_error:
                import traceback
                print(f"Error in addHost for router {name}: {str(add_error)}")
                print(f"Error type: {type(add_error)}")
                traceback.print_exc()
                raise Exception(f"Failed to create router: {str(add_error)}")
            
            try:
                result = router.cmd('sysctl -w net.ipv4.ip_forward=1')
                print(f"IP forwarding result: {result}")
            except Exception as ip_error:
                print(f"Warning: Failed to enable IP forwarding: {str(ip_error)}")

            self.nodes[name] = router
            
            print(f"Router interfaces: {[intf.name for intf in router.intfList()]}")
            for intf in router.intfList():
                if intf.name != 'lo':
                    print(f"Setting up interface {intf.name} on router {name}")
                    try:
                        result = router.cmd(f'ip link set {intf.name} up')
                        print(f"Interface up result: {result}")
                    except Exception as intf_error:
                        print(f"Warning: Error setting interface {intf.name} up: {str(intf_error)}")
            
            print(f"Router {name} added successfully")
            return router
        except Exception as e:
            import traceback
            print(f"Error adding router {name}: {str(e)}")
            print(f"Error type: {type(e)}")
            traceback.print_exc()
            raise

    def configure_router_interface(self, router_name, interface_name, ip_address, subnet_mask=24):
        """Настройка интерфейса на маршрутизаторе с IP-адресом"""
        print(f"Настройка интерфейса {interface_name} на маршрутизаторе {router_name}")
        
        router = self.get_node(router_name)
        if not router:
            print(f"ERROR: Router {router_name} not found")
            raise Exception(f"Router {router_name} not found")
        
        try:
            interfaces = [intf.name for intf in router.intfList()]
            print(f"Available interfaces on {router_name}: {interfaces}")
            
            if interface_name not in interfaces:
                print(f"Warning: Interface {interface_name} not found on router {router_name}")
                available_intf = next((intf for intf in interfaces if intf != 'lo'), None)
                if available_intf:
                    print(f"Using alternative interface {available_intf} instead of {interface_name}")
                    interface_name = available_intf
                else:
                    print(f"No suitable interfaces found on router {router_name}")
                    raise Exception(f"No suitable interfaces found on router {router_name}")
            
            if '/' not in ip_address:
                ip_address = f"{ip_address}/{subnet_mask}"
            
            try:
                print(f"Setting interface {interface_name} up")
                up_result = router.cmd(f'ip link set {interface_name} up')
                print(f"Interface up result: {up_result}")
            except Exception as up_error:
                print(f"Warning: Error setting interface up: {str(up_error)}")

            try:
                print(f"Adding IP {ip_address} to interface {interface_name}")
                ip_result = router.cmd(f'ip addr add {ip_address} dev {interface_name}')
                print(f"IP add result: {ip_result}")
                
                check_result = router.cmd(f"ip -o -4 addr show dev {interface_name}")
                print(f"IP verification result: {check_result}")
                
                if ip_address.split('/')[0] not in check_result:
                    print(f"Warning: IP {ip_address} may not have been set correctly on {interface_name}")
            except Exception as ip_error:
                print(f"Error adding IP to interface: {str(ip_error)}")
                raise
            
            print(f"Interface {interface_name} on router {router_name} configured with IP {ip_address}")
            return True
        except Exception as e:
            import traceback
            print(f"Error configuring router interface: {str(e)}")
            print(f"Error type: {type(e)}")
            traceback.print_exc()
            raise

    def add_route(self, router_name, network, next_hop=None, interface=None):
        """Добавление маршрута в таблицу маршрутизации маршрутизатора"""
        print(f"Добавление маршрута к {network} на маршрутизаторе {router_name}")
        
        router = self.get_node(router_name)
        if not router:
            print(f"ERROR: Router {router_name} not found")
            raise Exception(f"Router {router_name} not found")
        
        try:
            route_cmd = f'ip route add {network}'
            if next_hop:
                route_cmd += f' via {next_hop}'
            if interface:
                route_cmd += f' dev {interface}'
            
            router.cmd(route_cmd)
            
            print(f"Route to {network} added on router {router_name}")
            return True
        except Exception as e:
            print(f"Error adding route: {str(e)}")
            raise

class CustomTopology(Topo):
    def build(self, topology_config: dict):
        for host in topology_config.get('hosts', []):
            self.addHost(host['name'])
            
        for switch in topology_config.get('switches', []):
            self.addSwitch(switch['name'])
            
        for link in topology_config.get('links', []):
            self.addLink(link['node1'], link['node2']) 