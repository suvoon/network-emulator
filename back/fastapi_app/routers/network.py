from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from ..network.topology import NetworkTopology as TopologyManager
from ..network.packet_manager import PacketManager
from django.db import transaction
from django_app.models import NetworkTopology as DjangoNetworkTopology
from django_app.models import NetworkNode, PacketTrace
from django.contrib.auth.models import User
import asyncio
from ..network.packet_tracer import PacketTracer
from ..network.topology_validator import TopologyValidator
from asgiref.sync import sync_to_async
import subprocess
import time
from ..dependencies import get_current_active_user
import os
import re
import random
from concurrent.futures import ThreadPoolExecutor

class TopologyConfig(BaseModel):
    name: str = Field(..., description="Unique name for the topology")
    description: Optional[str] = Field(None, description="Optional description")
    hosts: List[Dict] = Field(
        ...,
        example=[
            {"name": "h1"},
            {"name": "h2"}
        ],
        description="List of hosts to create in the topology"
    )
    switches: List[Dict] = Field(
        ...,
        example=[
            {"name": "s1"}
        ],
        description="List of switches to create in the topology"
    )
    links: List[Dict] = Field(
        ...,
        example=[
            {"node1": "h1", "node2": "s1"},
            {"node1": "h2", "node2": "s1"}
        ],
        description="List of links between nodes"
    )
    routers: Optional[List[Dict]] = Field(
        None,
        description="Optional list of routers to create in the topology"
    )

class PacketConfig(BaseModel):
    source_node: str = Field(
        ..., 
        description="Name of the source node"
    )
    packet_config: Dict = Field(
        ...,
        description="Packet configuration including layers and payload"
    )
    interface: Optional[str] = Field(
        None,
        description="Optional interface name for sending the packet"
    )

class PacketTraceRequest(BaseModel):
    source_node: str
    destination_node: str
    packet_config: Dict
    protocol: Optional[str] = Field(None, description="Optional protocol for the packet")
    destination_port: Optional[int] = Field(None, description="Optional destination port for the packet")

class PingRequest(BaseModel):
    source_node: str
    destination_ip: str
    count: Optional[int] = 1

class TcpRequest(BaseModel):
    source_node: str
    destination_ip: str
    destination_port: int

class UdpRequest(BaseModel):
    source_node: str
    destination_ip: str
    destination_port: int
    message: str

class HttpRequest(BaseModel):
    source_node: str
    destination_ip: str
    port: Optional[int] = 80

class NewHostConfig(BaseModel):
    name: str = Field(..., description="Name of the new host")
    display_name: Optional[str] = Field(None, description="Display name for the host")
    ip: Optional[str] = Field(None, description="IP address for the host")
    x: Optional[float] = Field(None, description="X coordinate on canvas")
    y: Optional[float] = Field(None, description="Y coordinate on canvas")

class NewSwitchConfig(BaseModel):
    name: str = Field(..., description="Name of the new switch")
    display_name: Optional[str] = Field(None, description="Display name for the switch")
    ip: Optional[str] = Field(None, description="IP address for the switch management")
    x: Optional[float] = Field(None, description="X coordinate on canvas")
    y: Optional[float] = Field(None, description="Y coordinate on canvas")

class NewRouterConfig(BaseModel):
    name: str = Field(..., description="Name of the new router")
    display_name: Optional[str] = Field(None, description="Display name for the router")
    ip: Optional[str] = Field(None, description="IP address for the router")
    x: Optional[float] = Field(None, description="X coordinate on canvas")
    y: Optional[float] = Field(None, description="Y coordinate on canvas")
    interfaces: Optional[List[Dict]] = Field(
        None,
        description="Optional list of interfaces to configure on the router"
    )
    routes: Optional[List[Dict]] = Field(
        None,
        description="Optional list of routes to add to the router"
    )

class NewLinkConfig(BaseModel):
    node1: str = Field(..., description="Name of the first node")
    node2: str = Field(..., description="Name of the second node")

class DeleteLinkConfig(BaseModel):
    node1: str = Field(..., description="Name of the first node")
    node2: str = Field(..., description="Name of the second node")

class UpdateDisplayNameConfig(BaseModel):
    name: str = Field(..., description="Name of the device")
    display_name: str = Field(..., description="New display name for the device")

class UpdateNodePositionConfig(BaseModel):
    name: str = Field(..., description="Name of the device")
    x: float = Field(..., description="New X coordinate")
    y: float = Field(..., description="New Y coordinate")

class UpdateHostIpConfig(BaseModel):
    name: str = Field(..., description="Name of the host")
    ip: str = Field(..., description="New IP address for the host")

class UpdateSwitchIpConfig(BaseModel):
    name: str = Field(..., description="Name of the switch")
    ip: str = Field(..., description="New management IP address for the switch")

class UpdateRouterIpConfig(BaseModel):
    name: str = Field(..., description="Name of the router")
    ip: str = Field(..., description="New management IP address for the router")

class ConfigureRouterInterfaceRequest(BaseModel):
    router_name: str = Field(..., description="Name of the router")
    interface_name: str = Field(..., description="Name of the interface to configure")
    ip_address: str = Field(..., description="IP address to assign to the interface")
    subnet_mask: Optional[int] = Field(24, description="Subnet mask in CIDR notation (default: 24)")

router = APIRouter(
    prefix="/api/network",
    tags=["network"],
)

topology_manager = TopologyManager()
packet_manager = PacketManager()
packet_tracer = PacketTracer(topology_manager)
topology_validator = TopologyValidator(topology_manager)

@sync_to_async
def get_all_topologies_for_user(user: User):
    return list(DjangoNetworkTopology.objects.filter(user=user).values(
    'id', 'name', 'description', 'created_at', 'is_active'
    ))

@sync_to_async
def get_topology_by_id_for_user(topology_id: int, user: User):
    """Получение конкретной топологии по ID, принадлежащей данному пользователю"""
    return DjangoNetworkTopology.objects.get(id=topology_id, user=user)

@sync_to_async
def get_active_topology_for_user(user: User):
    """Получение активной топологии для конкретного пользователя"""
    try:
        return DjangoNetworkTopology.objects.get(is_active=True, user=user)
    except DjangoNetworkTopology.MultipleObjectsReturned:
        print("WARNING: Multiple active topologies found for user, using the first one")
        return DjangoNetworkTopology.objects.filter(is_active=True, user=user).first()

@sync_to_async
def get_active_topology(user: User = None):
    """Получение активной топологии для пользователя или любой активной топологии, если пользователь не указан"""
    if user:
        try:
            return DjangoNetworkTopology.objects.get(is_active=True, user=user)
        except DjangoNetworkTopology.MultipleObjectsReturned:
            print("WARNING: Multiple active topologies found for user, using the first one")
            return DjangoNetworkTopology.objects.filter(is_active=True, user=user).first()
    else:
        try:
            return DjangoNetworkTopology.objects.get(is_active=True)
        except DjangoNetworkTopology.MultipleObjectsReturned:
            print("WARNING: Multiple active topologies found, using the first one")
            return DjangoNetworkTopology.objects.filter(is_active=True).first()

@sync_to_async
def deactivate_all_topologies_for_user(user: User):
    count = DjangoNetworkTopology.objects.filter(is_active=True, user=user).count()
    if count > 1:
        print(f"WARNING: Found {count} active topologies for user {user.username}, deactivating all")
    result = DjangoNetworkTopology.objects.filter(is_active=True, user=user).update(is_active=False)
    print(f"Deactivated {result} active topologies for user {user.username}")
    return result

@sync_to_async
def create_topology_with_nodes(config: TopologyConfig, user: User):
    with transaction.atomic():
        DjangoNetworkTopology.objects.filter(is_active=True, user=user).update(is_active=False)
        
        topology = DjangoNetworkTopology.objects.create(
            name=config.name,
            description=config.description or "",
            hosts=config.hosts,
            switches=config.switches,
            links=config.links,
            routers=config.routers if hasattr(config, 'routers') else [],
            is_active=True,
            user=user
        )

        for host in config.hosts:
            NetworkNode.objects.create(
                topology=topology,
                name=host['name'],
                node_type='host',
                ip_address=host.get('ip')
            )

        for switch in config.switches:
            NetworkNode.objects.create(
                topology=topology,
                name=switch['name'],
                node_type='switch'
            )
            
        if hasattr(config, 'routers'):
            for router in config.routers:
                NetworkNode.objects.create(
                    topology=topology,
                    name=router['name'],
                    node_type='router',
                    ip_address=router.get('ip')
                )
        
        return topology

@router.post("/topology/create")
async def create_topology(config: TopologyConfig, current_user: User = Depends(get_current_active_user)):
    """Создание новой сетевой топологии и сохранение её в базе данных"""
    try:
        if not hasattr(config, 'routers'):
            config.routers = []
        elif config.routers is None:
            config.routers = []
        
        # Explicitly deactivate all topologies to avoid multiple active ones
        await deactivate_all_topologies_for_user(current_user)
            
        topology = await create_topology_with_nodes(config, current_user)
        await async_create_network(topology)
        return {
            "message": "Topology created successfully",
            "topology_id": topology.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/topology/list")
async def list_topologies(current_user: User = Depends(get_current_active_user)):
    """Получение списка всех сохранённых топологий для текущего пользователя"""
    try:
        topologies = await get_all_topologies_for_user(current_user)
        return topologies
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/topology/{topology_id}")
async def get_topology(topology_id: int, current_user: User = Depends(get_current_active_user)):
    """Получение деталей конкретной топологии, принадлежащей текущему пользователю"""
    try:
        topology = await get_topology_by_id_for_user(topology_id, current_user)
        return topology.get_topology_config()
    except DjangoNetworkTopology.DoesNotExist:
        raise HTTPException(status_code=404, detail=f"Topology {topology_id} not found or you don't have access to it")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def kill_controller():
    """Завершение работы контроллера"""
    try:
        subprocess.run(['pkill', 'ovs-testcontroller'], stderr=subprocess.PIPE)
        subprocess.run(['pkill', 'ovs-controller'], stderr=subprocess.PIPE)
        subprocess.run(['pkill', '-f', ':6653'], stderr=subprocess.PIPE)
        time.sleep(2)
    except Exception as e:
        print(f"Error killing controller: {e}")

def cleanup_mininet():
    """Очистка любого существующего состояния Mininet"""
    try:
        print("Начало комплексной очистки Mininet...")
        
        try:
            subprocess.run(['pkill', '-f', 'mininet'], stderr=subprocess.PIPE)
        except Exception as e:
            print(f"Error killing mininet processes: {e}")
            
        try:
            subprocess.run(['mn', '-c'], stderr=subprocess.PIPE)
        except Exception as e:
            print(f"Error running mn -c: {e}")
            
        try:
            result = subprocess.run(['ovs-vsctl', 'list-br'], stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            if result.returncode == 0 and result.stdout:
                bridges = result.stdout.strip().split('\n')
                for bridge in bridges:
                    if bridge:
                        print(f"Removing bridge: {bridge}")
                        subprocess.run(['ovs-vsctl', '--if-exists', 'del-br', bridge], stderr=subprocess.PIPE)
        except Exception as e:
            print(f"Error removing OVS bridges: {e}")
        
        try:
            subprocess.run(['pkill', '-f', 'ovs'], stderr=subprocess.PIPE)
        except Exception as e:
            print(f"Error killing OVS processes: {e}")
            
        try:
            subprocess.run(['pkill', '-f', 'controller'], stderr=subprocess.PIPE)
        except Exception as e:
            print(f"Error killing controller processes: {e}")
        
        try:
            os.system("ip link | grep veth | cut -d':' -f2 | cut -d'@' -f1 | xargs -I{} ip link delete {} 2>/dev/null || true")
        except Exception as e:
            print(f"Error cleaning leftover veth interfaces: {e}")
            
        print("Mininet cleanup completed")
        time.sleep(1)
    except Exception as e:
        print(f"Error during cleanup_mininet: {e}")

async def async_cleanup_mininet():
    """Асинхронная обёртка для cleanup_mininet"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, cleanup_mininet)

async def async_create_network(topology):
    """Асинхронное создание сети"""
    config = {
        'hosts': topology.hosts,
        'switches': topology.switches,
        'links': topology.links,
    }
    
    if hasattr(topology, 'routers') and topology.routers is not None:
        config['routers'] = topology.routers
    else:
        config['routers'] = []
    
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: topology_manager.create_network(config))

async def ensure_active_topology(current_user: User = None):
    """
    Убедиться, что в базе данных есть активная топология и Mininet
    Возвращает модель базы данных активной топологии
    """
    try:
        active_topology = await get_active_topology(current_user)
        
        if not hasattr(active_topology, 'routers') or active_topology.routers is None:
            active_topology.routers = []
            await sync_to_async(active_topology.save)()
        
        if not topology_manager.is_running():
            await async_create_network(active_topology)
        
        topology_manager.active_topology = active_topology
        
        return active_topology
    except DjangoNetworkTopology.DoesNotExist:
        raise HTTPException(
            status_code=400, 
            detail="No active topology. Please create or activate a topology first."
        )

@router.post("/topology/{topology_id}/activate")
async def activate_topology(topology_id: int, current_user: User = Depends(get_current_active_user)):
    """Активация сохранённой топологии и запуск эмулированной сети"""
    try:
        await deactivate_all_topologies_for_user(current_user)
        
        topology = await get_topology_by_id_for_user(topology_id, current_user)
        
        topology.is_active = True
        await sync_to_async(topology.save)()
        
        await async_cleanup_mininet()
        
        await async_create_network(topology)
        
        topology_manager.active_topology = topology
        
        print(f"Topology {topology.name} (ID: {topology_id}) activated successfully")
        
        if topology_manager.net:
            print("Verifying host IPs:")
            for host in topology_manager.net.hosts:
                if host.name.startswith('r'):
                    continue
                
                if not host.intfList() or len(host.intfList()) == 0:
                    print(f"Warning: Host {host.name} has no interfaces")
                    continue
                
                try:
                    ip = host.IP()
                    print(f"Host {host.name} has IP: {ip}")
                    
                    if not ip or ip == '0.0.0.0':
                        for db_host in topology.hosts:
                            if db_host['name'] == host.name and 'ip' in db_host and db_host['ip']:
                                db_ip = db_host['ip']
                                ip_parts = db_ip.split('/') if '/' in db_ip else [db_ip, '24']
                                ip_addr = ip_parts[0]
                                mask = ip_parts[1] if len(ip_parts) > 1 else '24'
                                
                                print(f"Setting IP {ip_addr}/{mask} on host {host.name} from database")
                                try:
                                    host.setIP(ip_addr, f"/{mask}")
                                    print(f"Host {host.name} IP updated to {host.IP()}")
                                except Exception as e:
                                    print(f"Error setting IP on host {host.name}: {str(e)}")
                                break
                except Exception as e:
                    print(f"Error checking IP for host {host.name}: {str(e)}")
        
        return {
            "success": True,
            "message": f"Topology {topology.name} activated successfully",
            "topology_id": topology_id
        }
    except DjangoNetworkTopology.DoesNotExist:
        raise HTTPException(
            status_code=404,
            detail=f"Topology with id {topology_id} not found"
        )
    except Exception as e:
        print(f"Error activating topology: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/topology/{topology_id}")
async def delete_topology(topology_id: int, current_user: User = Depends(get_current_active_user)):
    """Удаление сохранённой топологии"""
    try:
        topology = await get_topology_by_id_for_user(topology_id, current_user)
        
        if topology.is_active:
            await cleanup_mininet()
        
        await sync_to_async(topology.delete)()
        
        return {"message": f"Topology {topology_id} deleted successfully"}
    except DjangoNetworkTopology.DoesNotExist:
        raise HTTPException(status_code=404, detail=f"Topology {topology_id} not found or you don't have access to it")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@sync_to_async
def create_packet_trace(active_topology, trace_request):
    return PacketTrace.objects.create(
        topology=active_topology,
        source_node=trace_request.source_node,
        destination_node=trace_request.destination_node,
        packet_config=trace_request.packet_config,
        current_node=trace_request.source_node
    )

@sync_to_async
def get_packet_trace_by_id(trace_id: int):
    return PacketTrace.objects.get(id=trace_id)

@sync_to_async
def get_active_packet_traces():
    return list(PacketTrace.objects.exclude(state='completed').values(
        'id', 'source_node', 'destination_node', 'state', 'current_node', 'route'
    ))

@router.post("/packet/trace/start")
async def start_packet_trace(trace_request: PacketTraceRequest, current_user: User = Depends(get_current_active_user)):
    """Запуск трассировки пакета через сеть"""
    try:
        active_topology = await ensure_active_topology(current_user)
        
        if not hasattr(topology_manager, 'active_topology') or not topology_manager.active_topology:
            topology_manager.active_topology = active_topology
        
        source = topology_manager.get_node(trace_request.source_node)
        destination = topology_manager.get_node(trace_request.destination_node)
        
        if not source or not destination:
            print(f"Error: Source or destination node not found. Source: {trace_request.source_node} ({source}), Destination: {trace_request.destination_node} ({destination})")
            raise HTTPException(
                status_code=404,
                detail=f"Source or destination node not found: {trace_request.source_node if not source else ''} {trace_request.destination_node if not destination else ''}"
            )
        
        source_ip = None
        if hasattr(source, 'IP') and callable(source.IP):
            source_ip = source.IP()
        
        if not source_ip or source_ip == '0.0.0.0/0':
            print(f"Source node {trace_request.source_node} has no IP in Mininet, checking database")
            
            for host in active_topology.hosts:
                if host['name'] == trace_request.source_node and 'ip' in host and host['ip']:
                    source_ip = host['ip']
                    print(f"Found IP {source_ip} for host {trace_request.source_node} in database")
                    break
            
            if not source_ip and hasattr(active_topology, 'routers'):
                for router in active_topology.routers:
                    if router['name'] == trace_request.source_node:
                        if 'interfaces' in router and router['interfaces']:
                            first_interface = router['interfaces'][0]
                            if 'ip' in first_interface and first_interface['ip']:
                                source_ip = first_interface['ip']
                                print(f"Using router interface IP {source_ip} for router {trace_request.source_node}")
                                break
        
        if not source_ip:
            print(f"Error: Source node {trace_request.source_node} has no IP address")
            raise HTTPException(
                status_code=400,
                detail=f"Source node {trace_request.source_node} has no IP address"
            )
            
        print(f"Starting packet trace from {trace_request.source_node} ({source_ip}) to {trace_request.destination_node}")
        
        protocol = trace_request.protocol.lower() if trace_request.protocol else "icmp"
        packet_config = {
            "protocol": protocol
        }
        
        if protocol in ["tcp", "udp", "http"]:
            packet_config["dport"] = trace_request.destination_port if trace_request.destination_port else (80 if protocol == "http" else 8080)
            packet_config["sport"] = random.randint(1024, 65535)
            
        if protocol == "http":
            packet_config["method"] = "GET"
            packet_config["path"] = "/"
        
        trace_id = f"trace-{time.time()}"
        
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor() as executor:
            executor.submit(packet_tracer.start_trace, trace_id, trace_request.source_node, trace_request.destination_node, packet_config)
        
        return {"trace_id": trace_id}
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to start packet trace: {str(e)}"
        )

@router.get("/packet/trace/{trace_id}")
async def get_packet_trace(trace_id: str):
    """Получение текущего состояния пакета"""
    try:
        trace_info = packet_tracer.get_trace_info(trace_id)
        if trace_info:
            success = (
                trace_info["state"] == "completed" 
                and trace_info["current_node"] == trace_info["destination"]
                and not trace_info.get("error")
            )
            
            return {
                "id": trace_id,
                "source_node": trace_info["source"],
                "destination_node": trace_info["destination"],
                "state": trace_info["state"],
                "current_node": trace_info["current_node"],
                "source_ip": trace_info.get("source_ip"),
                "destination_ip": trace_info.get("destination_ip"),
                "route": [],
                "hops": [
                    {
                        "node": hop["node"],
                        "time": hop["time"],
                        "action": hop["action"],
                        "details": hop.get("details", "")
                    }
                    for hop in trace_info.get("hops", [])
                ],
                "completed": trace_info["state"] == "completed",
                "success": success,
                "error": trace_info.get("error")
            }
        
        try:
            if trace_id.isdigit():
                db_trace_id = int(trace_id) 
                trace = await get_packet_trace_by_id(db_trace_id)
                
                trace_info = packet_tracer.get_trace_info(db_trace_id)
                
                success = (
                    trace_info 
                    and trace_info["state"] == "completed" 
                    and trace_info["current_node"] == trace_info["destination"]
                    and not trace_info.get("error")
                )
                
                return {
                    "id": trace.id,
                    "source_node": trace.source_node,
                    "destination_node": trace.destination_node,
                    "state": trace_info["state"] if trace_info else trace.state,
                    "current_node": trace_info["current_node"] if trace_info else trace.current_node,
                    "route": trace.route,
                    "hops": [
                        {
                            "node": hop["node"],
                            "time": hop["time"],
                            "action": hop["action"],
                            "details": hop.get("details", "")
                        }
                        for hop in (trace_info.get("hops", []) if trace_info else [])
                    ],
                    "completed": trace_info["state"] == "completed" if trace_info else False,
                    "success": success,
                    "error": trace_info.get("error") if trace_info else None
                }
            else:
                raise HTTPException(status_code=404, detail="Trace not found")
                
        except (ValueError, PacketTrace.DoesNotExist):
            raise HTTPException(status_code=404, detail="Trace not found")
    except Exception as e:
        print(f"Error retrieving trace {trace_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/packet/trace/{trace_id}")
async def stop_packet_trace(trace_id: str):
    """Остановка пакетной трассировки"""
    try:
        if trace_id in packet_tracer.traces:
            packet_tracer.stop_trace(trace_id)
            return {"message": "Packet trace stopped"}
            
        if trace_id.isdigit():
            db_trace_id = int(trace_id)
            trace = await get_packet_trace_by_id(db_trace_id)
            
            packet_tracer.stop_trace(db_trace_id)
            
            trace.state = 'completed'
            await sync_to_async(trace.save)()
            return {"message": "Packet trace stopped"}
            
        raise HTTPException(status_code=404, detail="Trace not found")
    except PacketTrace.DoesNotExist:
        if trace_id in packet_tracer.traces:
            return {"message": "Packet trace stopped (memory only)"}
        raise HTTPException(status_code=404, detail="Trace not found")
    except Exception as e:
        print(f"Error stopping trace {trace_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/packet/send")
async def send_packet(packet_config: PacketConfig):
    """Отправка пакета от узла"""
    node = topology_manager.get_node(packet_config.source_node)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    packet = packet_manager.create_packet(packet_config.packet_config)
    if not packet:
        raise HTTPException(status_code=400, detail="Invalid packet configuration")
    
    try:
        packet_manager.send_packet(node, packet, packet_config.interface)
        return {"message": "Packet sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/packet/ping")
async def ping_host(request: PingRequest):
    """Пинг узла от узла-источника"""
    try:
        count = request.count if request.count and request.count > 0 else 1
        
        active_topology = await ensure_active_topology(None)
        
        if not hasattr(topology_manager, 'active_topology') or not topology_manager.active_topology:
            topology_manager.active_topology = active_topology
            
        source_node = topology_manager.get_node(request.source_node)
        if not source_node:
            print(f"Error: Source node not found: {request.source_node}")
            raise HTTPException(status_code=404, detail=f"Source node not found: {request.source_node}")
            
        source_ip = None
        if hasattr(source_node, 'IP') and callable(source_node.IP):
            source_ip = source_node.IP()
        
        if not source_ip or source_ip == '0.0.0.0':
            print(f"Source node {request.source_node} has no IP in Mininet, checking database")
            
            for host in active_topology.hosts:
                if host['name'] == request.source_node and 'ip' in host and host['ip']:
                    db_ip = host['ip']
                    ip_only = db_ip.split('/')[0] if '/' in db_ip else db_ip
                    mask = db_ip.split('/')[1] if '/' in db_ip else '24'
                    
                    try:
                        source_node.setIP(ip_only, f"/{mask}")
                        source_ip = source_node.IP()
                        print(f"Set IP {source_ip} on host {request.source_node} from database")
                    except Exception as e:
                        print(f"Error setting IP from database: {str(e)}")
                        source_ip = db_ip
                    break
                    
            if (not source_ip or source_ip == '0.0.0.0') and hasattr(active_topology, 'routers'):
                for router in active_topology.routers:
                    if router['name'] == request.source_node:
                        if 'ip' in router and router['ip']:
                            db_ip = router['ip']
                            ip_only = db_ip.split('/')[0] if '/' in db_ip else db_ip
                            mask = db_ip.split('/')[1] if '/' in db_ip else '24'
                            
                            try:
                                source_node.setIP(ip_only, f"/{mask}")
                                source_ip = source_node.IP()
                                print(f"Set IP {source_ip} on router {request.source_node} from database")
                            except Exception as e:
                                print(f"Error setting IP from database: {str(e)}")
                                source_ip = db_ip
                            break
                            
                        if (not source_ip or source_ip == '0.0.0.0') and 'interfaces' in router and router['interfaces']:
                            for intf in router['interfaces']:
                                if 'ip' in intf and intf['ip']:
                                    db_ip = intf['ip']
                                    ip_only = db_ip.split('/')[0] if '/' in db_ip else db_ip
                                    mask = db_ip.split('/')[1] if '/' in db_ip else str(intf.get('subnet_mask', '24'))
                                    
                                    try:
                                        source_node.setIP(ip_only, f"/{mask}")
                                        source_ip = source_node.IP()
                                        print(f"Set IP {source_ip} on router {request.source_node} from interface {intf.get('name')} in database")
                                    except Exception as e:
                                        print(f"Error setting IP from database: {str(e)}")
                                    break
            
            if not source_ip or source_ip == '0.0.0.0':
                raise HTTPException(
                    status_code=400, 
                    detail=f"Source node {request.source_node} has no IP address in Mininet or database"
                )

        ping_results = packet_tracer.ping(
            request.source_node, 
            request.destination_ip,
            count
        )
        
        return ping_results
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error performing ping: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/packet/tcp")
async def tcp_connect(request: TcpRequest):
    """Попытка установить TCP-соединение от узла-источника к узлу-назначению"""
    source = topology_manager.get_node(request.source_node)
    if not source:
        raise HTTPException(status_code=404, detail="Source node not found")
    
    try:
        result = packet_manager.tcp_connection(
            source, 
            request.destination_ip, 
            request.destination_port
        )
        return {"message": "TCP connection attempt completed", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/packet/udp")
async def udp_send(request: UdpRequest):
    """Отправка UDP-сообщения от узла-источника к узлу-назначению"""
    source = topology_manager.get_node(request.source_node)
    if not source:
        raise HTTPException(status_code=404, detail="Source node not found")
    
    try:
        result = packet_manager.udp_send(
            source, 
            request.destination_ip, 
            request.destination_port,
            request.message
        )
        return {"message": "UDP message sent", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/packet/http")
async def http_request(request: HttpRequest):
    """Отправка HTTP GET-запроса от узла-источника к узлу-назначению"""
    source = topology_manager.get_node(request.source_node)
    if not source:
        raise HTTPException(status_code=404, detail="Source node not found")
    
    try:
        result = packet_manager.http_request(source, request.destination_ip, request.port)
        return {"message": "HTTP request completed", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@sync_to_async
def get_topology_by_name(name: str):
    """Получение топологии по имени, возвращает None, если не найдена"""
    try:
        return DjangoNetworkTopology.objects.get(name=name)
    except DjangoNetworkTopology.DoesNotExist:
        return None

@router.post("/node/host")
async def add_host(config: NewHostConfig, current_user: User = Depends(get_current_active_user)):
    """Добавление нового узла в активную топологию"""
    try:
        active_topology = await ensure_active_topology(current_user)
        
        print(f"Adding host with config: {config}")
        
        if not topology_manager.net:
            print(f"ERROR: Cannot add host {config.name}: No switches available in the network")
            raise HTTPException(
                status_code=400,
                detail="Cannot add host: No switches available in the network. Please add a switch first."
            )
        
        existing_hosts = [h['name'] for h in active_topology.hosts]
        if config.name in existing_hosts:
            print(f"ERROR: Host with name {config.name} already exists")
            raise HTTPException(
                status_code=400, 
                detail=f"Host with name {config.name} already exists"
            )
        
        print("Attempting to add host to topology manager")
        host = topology_manager.add_host(config.name, config.ip)
        
        if not host:
            print(f"ERROR: Failed to create host {config.name}")
            raise Exception("Failed to create host")
        
        assigned_ip = host.IP()
        if not assigned_ip:
            print(f"ERROR: Failed to assign IP to host {config.name}")
            raise Exception("Failed to assign IP to host")
            
        print(f"Host added to topology manager: {host} with IP {assigned_ip}")
        
        active_topology.hosts.append({
            "name": config.name,
            "ip": assigned_ip,
            "display_name": config.display_name or config.name,
            "x": config.x or 100,
            "y": config.y or 100,
        })
        await sync_to_async(active_topology.save)()
        print("Database updated with new host")
        
        return {
            "success": True,
            "message": "Хост успешно добавлен",
            "name": config.name,
            "display_name": config.display_name or config.name,
            "ip": assigned_ip,
            "x": config.x or 100,
            "y": config.y or 100
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR adding host: {str(e)}")
        print(f"Current topology manager state: net={topology_manager.net}, nodes={topology_manager.nodes}, switches={len(topology_manager.net.switches) if topology_manager.net else 0}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/node/switch")
async def add_switch(config: NewSwitchConfig, current_user: User = Depends(get_current_active_user)):
    """Добавление нового коммутатора в активную топологию"""
    try:
        active_topology = await ensure_active_topology(current_user)
        
        print(f"Adding switch with config: {config}")
        
        existing_switches = [s['name'] for s in active_topology.switches]
        if config.name in existing_switches:
            print(f"ERROR: Switch with name {config.name} already exists")
            raise HTTPException(
                status_code=400,
                detail=f"Switch with name {config.name} already exists"
            )

        try:
            print(f"Adding switch {config.name} to topology")
            print(f"Current network state: net={topology_manager.net is not None}, nodes={len(topology_manager.nodes)}")
            switch = topology_manager.add_switch(config.name)
            if not switch:
                print(f"ERROR: Failed to create switch {config.name}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create switch"
                )
            print(f"Switch {config.name} added successfully")
        except Exception as e:
            print(f"Error creating switch: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create switch: {str(e)}"
            )
        
        ip_address = config.ip
        if not ip_address:
            try:
                ip_address = topology_manager.assign_ip_to_switch(config.name)
                print(f"Assigned IP {ip_address} to switch {config.name}")
            except Exception as e:
                print(f"Warning: Failed to assign IP to switch: {str(e)}")
        else:
            topology_manager.assign_ip_to_switch(config.name, ip_address)
            print(f"Used provided IP {ip_address} for switch {config.name}")
        
        try:
            active_topology.switches.append({
                "name": config.name,
                "display_name": config.display_name or config.name,
                "ip": ip_address,
                "x": config.x or 200,
                "y": config.y or 200
            })
            await sync_to_async(active_topology.save)()
            print("Database updated with new switch")
        except Exception as e:
            print(f"Error updating database: {str(e)}")
            if topology_manager.net:
                try:
                    topology_manager.net.removeSwitch(switch)
                except Exception as remove_error:
                    print(f"Error removing switch after database error: {str(remove_error)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to save switch to database"
            )
        
        return {
            "success": True,
            "message": "Коммутатор успешно добавлен",
            "name": config.name,
            "display_name": config.display_name or config.name,
            "ip": ip_address,
            "x": config.x or 200,
            "y": config.y or 200
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error adding switch: {str(e)}")
        print(f"Current topology manager state: net={topology_manager.net}, nodes={topology_manager.nodes}")
        raise HTTPException(
            status_code=500,
            detail=str(e) if str(e) else "Unknown error occurred while adding switch"
        )

@router.post("/node/router")
async def add_router(config: NewRouterConfig, current_user: User = Depends(get_current_active_user)):
    """Добавление нового маршрутизатора в активную топологию"""
    try:
        active_topology = await ensure_active_topology(current_user)
        
        print(f"Adding router with config: {config}")
        
        if not hasattr(active_topology, 'routers'):
            active_topology.routers = []
            
        existing_routers = [r['name'] for r in active_topology.routers] if hasattr(active_topology, 'routers') else []
        if config.name in existing_routers:
            print(f"ERROR: Router with name {config.name} already exists")
            raise HTTPException(
                status_code=400,
                detail=f"Router with name {config.name} already exists"
            )

        try:
            print(f"Adding router {config.name} to topology")
            print(f"Current network state: net={topology_manager.net is not None}, nodes={len(topology_manager.nodes)}")
            router = topology_manager.add_router(config.name)
            if not router:
                print(f"ERROR: Failed to create router {config.name}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create router"
                )
            print(f"Router {config.name} added successfully")
        except Exception as e:
            print(f"Error creating router: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create router: {str(e)}"
            )
        
        ip_address = config.ip
        
        if config.interfaces:
            for intf in config.interfaces:
                try:
                    topology_manager.configure_router_interface(
                        config.name,
                        intf['name'],
                        intf['ip'],
                        intf.get('subnet_mask', 24)
                    )
                except Exception as e:
                    print(f"Error configuring router interface: {str(e)}")
        
        if config.routes:
            for route in config.routes:
                try:
                    topology_manager.add_route(
                        config.name,
                        route['network'],
                        route.get('next_hop'),
                        route.get('interface')
                    )
                except Exception as e:
                    print(f"Error adding route to router: {str(e)}")
        
        try:
            if not hasattr(active_topology, 'routers'):
                active_topology.routers = []
                
            active_topology.routers.append({
                "name": config.name,
                "display_name": config.display_name or config.name,
                "ip": ip_address,
                "x": config.x or 300,
                "y": config.y or 300,
                "interfaces": config.interfaces or [],
                "routes": config.routes or []
            })
            await sync_to_async(active_topology.save)()
            print("Database updated with new router")
        except Exception as e:
            print(f"Error updating database: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to save router to database"
            )
        
        return {
            "success": True,
            "message": "Маршрутизатор успешно добавлен",
            "name": config.name,
            "display_name": config.display_name or config.name,
            "ip": ip_address,
            "x": config.x or 300,
            "y": config.y or 300
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error adding router: {str(e)}")
        print(f"Current topology manager state: net={topology_manager.net}, nodes={topology_manager.nodes}")
        raise HTTPException(
            status_code=500,
            detail=str(e) if str(e) else "Unknown error occurred while adding router"
        )

@router.delete("/node/router/{router_name}")
async def delete_router(router_name: str, current_user: User = Depends(get_current_active_user)):
    """Удаление маршрутизатора из активной топологии"""
    try:
        active_topology = await ensure_active_topology(current_user)
        
        if not hasattr(active_topology, 'routers'):
            raise HTTPException(
                status_code=404,
                detail="No routers found in topology"
            )
        
        router_exists = False
        router_index = -1
        
        for i, router in enumerate(active_topology.routers):
            if router['name'] == router_name:
                router_exists = True
                router_index = i
                break
                
        if not router_exists:
            raise HTTPException(
                status_code=404,
                detail=f"Router with name {router_name} not found"
            )
            
        router_node = topology_manager.get_node(router_name)
        if not router_node:
            print(f"Warning: Router {router_name} not found in topology manager")
        else:
            try:
                print(f"Removing router {router_name} from network")
                
                if topology_manager.net:
                    for intf in router_node.intfList():
                        if intf.link:
                            try:
                                topology_manager.net.delLink(intf.link)
                                print(f"Removed link from {router_name}")
                            except Exception as e:
                                print(f"Error removing link from router: {str(e)}")
                
                if topology_manager.net:
                    topology_manager.net.delNode(router_node)
                
                if router_name in topology_manager.nodes:
                    del topology_manager.nodes[router_name]
                    
                print(f"Router {router_name} removed from network")
            except Exception as e:
                print(f"Error removing router from network: {str(e)}")
        
        active_topology.routers.pop(router_index)
        await sync_to_async(active_topology.save)()
        print(f"Router {router_name} removed from database")
        
        return {
            "success": True,
            "message": f"Router {router_name} deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting router: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e) if str(e) else "Unknown error occurred while deleting router"
        )

@router.put("/node/router/ip")
async def update_router_ip(config: UpdateRouterIpConfig, current_user: User = Depends(get_current_active_user)):
    """Обновление IP-адреса маршрутизатора"""
    try:
        active_topology = await ensure_active_topology(current_user)
        
        if not hasattr(active_topology, 'routers'):
            raise HTTPException(
                status_code=404,
                detail="No routers found in topology"
            )
            
        router_found = False
        for router in active_topology.routers:
            if router['name'] == config.name:
                router_found = True
                router['ip'] = config.ip
                break
                
        if not router_found:
            raise HTTPException(
                status_code=404,
                detail=f"Router with name {config.name} not found"
            )
            
        router_node = topology_manager.get_node(config.name)
        if not router_node:
            raise HTTPException(
                status_code=404,
                detail=f"Router {config.name} not found in network"
            )
            
        try:
            intf = None
            for interface in router_node.intfList():
                if interface.name != 'lo':
                    intf = interface.name
                    break
                    
            if intf:
                topology_manager.configure_router_interface(config.name, intf, config.ip)
                print(f"Updated IP for router {config.name} on interface {intf} to {config.ip}")
            else:
                print(f"Warning: No suitable interface found on router {config.name}")
                
            await sync_to_async(active_topology.save)()
            
            return {
                "success": True,
                "message": "Router IP updated successfully",
                "name": config.name,
                "ip": config.ip
            }
        except Exception as e:
            print(f"Error setting IP on router: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to set IP on router: {str(e)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating router IP: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/link")
async def add_link(config: NewLinkConfig, current_user: User = Depends(get_current_active_user)):
    """Добавление новой связи между двумя узлами в активную топологию"""
    try:
        active_topology = await ensure_active_topology(current_user)
        
        print(f"Adding link between {config.node1} and {config.node2}")
        print(f"Current topology state: nodes={list(topology_manager.nodes.keys() if topology_manager.nodes else [])}")
        
        node1 = topology_manager.get_node(config.node1)
        node2 = topology_manager.get_node(config.node2)
        
        if not node1:
            print(f"ERROR: Node {config.node1} not found")
            raise HTTPException(
                status_code=404,
                detail=f"Node {config.node1} not found"
            )
            
        if not node2:
            print(f"ERROR: Node {config.node2} not found")
            raise HTTPException(
                status_code=404,
                detail=f"Node {config.node2} not found"
            )
        
        print(f"Nodes found: {config.node1} and {config.node2}")
        
        for link in active_topology.links:
            if (link['node1'] == config.node1 and link['node2'] == config.node2) or \
               (link['node1'] == config.node2 and link['node2'] == config.node1):
                print(f"WARNING: Link between {config.node1} and {config.node2} already exists")
                return {
                    "success": True,
                    "message": "Link already exists",
                    "node1": config.node1,
                    "node2": config.node2
                }
        
        try:
            topology_manager.add_link(config.node1, config.node2)
            print(f"Link added successfully between {config.node1} and {config.node2}")
        except Exception as e:
            print(f"ERROR adding link: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to add link: {str(e)}"
            )
        
        try:
            active_topology.links.append({
                "node1": config.node1,
                "node2": config.node2
            })
            await sync_to_async(active_topology.save)()
            print("Database updated with new link")
        except Exception as db_error:
            print(f"ERROR updating database: {str(db_error)}")
        
        return {
            "success": True,
            "message": "Связь успешно добавлена",
            "node1": config.node1,
            "node2": config.node2
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error adding link: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/link")
async def delete_link(config: DeleteLinkConfig, current_user: User = Depends(get_current_active_user)):
    """Удаление связи между двумя узлами"""
    try:
        active_topology = await ensure_active_topology(current_user)
        
        node1 = topology_manager.get_node(config.node1)
        node2 = topology_manager.get_node(config.node2)
        
        if not node1 or not node2:
            raise HTTPException(status_code=404, detail="One or both nodes not found")
            
        topology_manager.net.delLinkBetween(node1, node2)
        
        return {
            "message": "Link deleted successfully",
            "node1": config.node1,
            "node2": config.node2
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/node/display-name")
async def update_display_name(config: UpdateDisplayNameConfig, current_user: User = Depends(get_current_active_user)):
    """Обновление имени узла"""
    try:
        active_topology = await ensure_active_topology(current_user)
        
        for host in active_topology.hosts:
            if host['name'] == config.name:
                host['display_name'] = config.display_name
                await sync_to_async(active_topology.save)()
                return {
                    "success": True,
                    "message": "Display name updated successfully",
                    "name": config.name,
                    "display_name": config.display_name
                }
        
        for switch in active_topology.switches:
            if switch['name'] == config.name:
                switch['display_name'] = config.display_name
                await sync_to_async(active_topology.save)()
                return {
                    "success": True,
                    "message": "Display name updated successfully",
                    "name": config.name,
                    "display_name": config.display_name
                }
        
        if hasattr(active_topology, 'routers'):
            for router in active_topology.routers:
                if router['name'] == config.name:
                    router['display_name'] = config.display_name
                    await sync_to_async(active_topology.save)()
                    return {
                        "success": True,
                        "message": "Display name updated successfully",
                        "name": config.name,
                        "display_name": config.display_name
                    }
        
        raise HTTPException(
            status_code=404,
            detail=f"Device with name {config.name} not found"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/node/position")
async def update_node_position(config: UpdateNodePositionConfig, current_user: User = Depends(get_current_active_user)):
    """Обновление позиции (координат x, y) узла"""
    try:
        print(f"Received position update request: {config}")
        active_topology = await ensure_active_topology(current_user)
        
        for host in active_topology.hosts:
            if host['name'] == config.name:
                print(f"Updating host position: {config.name} to x={config.x}, y={config.y}")
                host['x'] = config.x
                host['y'] = config.y
                await sync_to_async(active_topology.save)()
                print(f"Host position updated successfully")
                return {
                    "success": True,
                    "message": "Position updated successfully",
                    "name": config.name,
                    "x": config.x,
                    "y": config.y
                }
        
        for switch in active_topology.switches:
            if switch['name'] == config.name:
                print(f"Updating switch position: {config.name} to x={config.x}, y={config.y}")
                switch['x'] = config.x
                switch['y'] = config.y
                await sync_to_async(active_topology.save)()
                print(f"Switch position updated successfully")
                return {
                    "success": True,
                    "message": "Position updated successfully",
                    "name": config.name,
                    "x": config.x,
                    "y": config.y
                }
        
        if hasattr(active_topology, 'routers'):
            for router in active_topology.routers:
                if router['name'] == config.name:
                    print(f"Updating router position: {config.name} to x={config.x}, y={config.y}")
                    router['x'] = config.x
                    router['y'] = config.y
                    await sync_to_async(active_topology.save)()
                    print(f"Router position updated successfully")
                    return {
                        "success": True,
                        "message": "Position updated successfully",
                        "name": config.name,
                        "x": config.x,
                        "y": config.y
                    }
        
        print(f"Device not found: {config.name}")
        raise HTTPException(
            status_code=404,
            detail=f"Device with name {config.name} not found"
        )
    except Exception as e:
        print(f"Error updating position: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/node/host/ip")
async def update_host_ip(config: UpdateHostIpConfig, current_user: User = Depends(get_current_active_user)):
    """Update the IP address of a host"""
    try:
        active_topology = await ensure_active_topology(current_user)
        
        host_found = False
        for host in active_topology.hosts:
            if host['name'] == config.name:
                host_found = True
                host['ip'] = config.ip
                break
                
        if not host_found:
            raise HTTPException(
                status_code=404,
                detail=f"Host with name {config.name} not found"
            )
            
        host_node = topology_manager.get_node(config.name)
        if not host_node:
            raise HTTPException(
                status_code=404,
                detail=f"Host {config.name} not found in network topology"
            )
            
        try:
            ip_parts = config.ip.split('/')
            ip = ip_parts[0]
            netmask = '24'
            if len(ip_parts) > 1:
                netmask = ip_parts[1]
                
            host_node.setIP(ip, f"/{netmask}")
            print(f"Updated IP for host {config.name} to {config.ip}")
            
            host_node.cmd('sysctl -w net.ipv4.ip_forward=1')
            
            check_result = host_node.cmd("ip -o -4 addr show")
            print(f"IP verification for {config.name}: {check_result}")
            
            await sync_to_async(active_topology.save)()
            
            return {
                "success": True,
                "message": "Host IP updated successfully",
                "name": config.name,
                "ip": config.ip
            }
        except Exception as e:
            print(f"Error setting IP on host: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to set IP on host: {str(e)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating host IP: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/node/switch/ip")
async def update_switch_ip(config: UpdateSwitchIpConfig, current_user: User = Depends(get_current_active_user)):
    """Update the management IP address of a switch"""
    try:
        active_topology = await ensure_active_topology(current_user)
        
        switch_found = False
        for switch in active_topology.switches:
            if switch['name'] == config.name:
                switch_found = True
                switch['ip'] = config.ip
                break
                
        if not switch_found:
            raise HTTPException(
                status_code=404,
                detail=f"Switch with name {config.name} not found"
            )
            
        try:
            topology_manager.assign_ip_to_switch(config.name, config.ip)
            print(f"Updated IP for switch {config.name} to {config.ip}")
            
            await sync_to_async(active_topology.save)()
            
            return {
                "success": True,
                "message": "Switch IP updated successfully",
                "name": config.name,
                "ip": config.ip
            }
        except Exception as e:
            print(f"Error setting IP on switch: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to set IP on switch: {str(e)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating switch IP: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/topology-validate")
async def validate_topology(current_user: User = Depends(get_current_active_user)):
    """Валидация активной топологии"""
    try:
        await ensure_active_topology(current_user)
        
        validation_result = topology_validator.validate_topology()
        
        return validation_result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/node/host/{host_id}")
async def delete_host(host_id: str, current_user: User = Depends(get_current_active_user)):
    """Удалить хост из активной топологии"""
    try:
        active_topology = await ensure_active_topology(current_user)
        
        host_index = None
        for i, host in enumerate(active_topology.hosts):
            if host['name'] == host_id:
                host_index = i
                break
                
        if host_index is None:
            raise HTTPException(
                status_code=404,
                detail=f"Хост с именем {host_id} не найден"
            )
        
        try:
            host_node = topology_manager.get_node(host_id)
            if host_node:
                for intf in host_node.intfList():
                    if intf.link:
                        topology_manager.net.delLink(intf.link)
                        
                topology_manager.net.delHost(host_node)
                del topology_manager.nodes[host_id]
        except Exception as e:
            print(f"Ошибка при удалении хоста из Mininet: {str(e)}")
        
        del active_topology.hosts[host_index]
        
        active_topology.links = [
            link for link in active_topology.links 
            if link['node1'] != host_id and link['node2'] != host_id
        ]
        
        await sync_to_async(active_topology.save)()
        
        return {
            "success": True,
            "message": f"Хост {host_id} успешно удален"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Ошибка при удалении хоста: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/node/switch/{switch_id}")
async def delete_switch(switch_id: str, current_user: User = Depends(get_current_active_user)):
    """Удалить коммутатор из активной топологии"""
    try:
        active_topology = await ensure_active_topology(current_user)
        
        switch_index = None
        for i, switch in enumerate(active_topology.switches):
            if switch['name'] == switch_id:
                switch_index = i
                break
                
        if switch_index is None:
            raise HTTPException(
                status_code=404,
                detail=f"Коммутатор с именем {switch_id} не найден"
            )
        
        try:
            switch_node = topology_manager.get_node(switch_id)
            if switch_node:
                for intf in switch_node.intfList():
                    if intf.link:
                        topology_manager.net.delLink(intf.link)
                        
                topology_manager.net.delSwitch(switch_node)
                del topology_manager.nodes[switch_id]
        except Exception as e:
            print(f"Ошибка при удалении коммутатора из Mininet: {str(e)}")
        
        del active_topology.switches[switch_index]
        
        active_topology.links = [
            link for link in active_topology.links 
            if link['node1'] != switch_id and link['node2'] != switch_id
        ]
        
        await sync_to_async(active_topology.save)()
        
        return {
            "success": True,
            "message": f"Коммутатор {switch_id} успешно удален"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Ошибка при удалении коммутатора: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/node/router/interface")
async def configure_router_interface(config: ConfigureRouterInterfaceRequest, current_user: User = Depends(get_current_active_user)):
    """Настройка интерфейса маршрутизатора"""
    try:
        active_topology = await ensure_active_topology(current_user)
        
        if not hasattr(active_topology, 'routers'):
            raise HTTPException(
                status_code=404,
                detail="No routers found in topology"
            )
            
        router_found = False
        router_index = -1
        for i, router in enumerate(active_topology.routers):
            if router['name'] == config.router_name:
                router_found = True
                router_index = i
                break
                
        if not router_found:
            raise HTTPException(
                status_code=404,
                detail=f"Router with name {config.router_name} not found"
            )
            
        router_node = topology_manager.get_node(config.router_name)
        if not router_node:
            raise HTTPException(
                status_code=404,
                detail=f"Router {config.router_name} not found in network"
            )
            
        try:
            topology_manager.configure_router_interface(
                config.router_name,
                config.interface_name,
                config.ip_address,
                config.subnet_mask
            )
            print(f"Updated IP for router {config.router_name} on interface {config.interface_name} to {config.ip_address}")
            
            if 'interfaces' not in active_topology.routers[router_index]:
                active_topology.routers[router_index]['interfaces'] = []
                
            formatted_ip = config.ip_address
            if '/' not in formatted_ip:
                formatted_ip = f"{formatted_ip}/{config.subnet_mask}"
                
            interface_exists = False
            for i, intf in enumerate(active_topology.routers[router_index].get('interfaces', [])):
                if intf.get('name') == config.interface_name:
                    active_topology.routers[router_index]['interfaces'][i] = {
                        'name': config.interface_name,
                        'ip': formatted_ip,
                        'subnet_mask': config.subnet_mask
                    }
                    interface_exists = True
                    break
                    
            if not interface_exists:
                active_topology.routers[router_index]['interfaces'].append({
                    'name': config.interface_name,
                    'ip': formatted_ip,
                    'subnet_mask': config.subnet_mask
                })
            
            await sync_to_async(active_topology.save)()
            
            return {
                "success": True,
                "message": "Router interface updated successfully",
                "name": config.router_name,
                "interface": config.interface_name,
                "ip_address": config.ip_address,
                "subnet_mask": config.subnet_mask
            }
        except Exception as e:
            print(f"Error configuring router interface: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to configure router interface: {str(e)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error configuring router interface: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/node/router/{router_id}/interfaces")
async def get_router_interfaces(router_id: str, current_user: User = Depends(get_current_active_user)):
    """Получение всех интерфейсов из маршрутизатора"""
    try:
        active_topology = await ensure_active_topology(current_user)
        
        if not hasattr(active_topology, 'routers'):
            raise HTTPException(
                status_code=404,
                detail="No routers found in topology"
            )
            
        router_found = False
        router_config = None
        for router in active_topology.routers:
            if router['name'] == router_id:
                router_found = True
                router_config = router
                break
                
        if not router_found:
            raise HTTPException(
                status_code=404,
                detail=f"Router with name {router_id} not found"
            )
            
        router_node = topology_manager.get_node(router_id)
        if not router_node:
            raise HTTPException(
                status_code=404,
                detail=f"Router {router_id} not found in network"
            )
        
        mininet_interfaces = []
        try:
            for intf in router_node.intfList():
                if intf.name != 'lo':
                    ip_cmd_result = router_node.cmd(f"ip -o -4 addr show {intf.name}")
                    ip_address = None
                    subnet_mask = None
                    
                    if ip_cmd_result:
                        ip_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)(?:/(\d+))?', ip_cmd_result)
                        if ip_match:
                            ip_address = ip_match.group(1)
                            subnet_mask = int(ip_match.group(2) or 24)
                    
                    mininet_interfaces.append({
                        "name": intf.name,
                        "ip": f"{ip_address}/{subnet_mask}" if ip_address else None,
                        "subnet_mask": subnet_mask
                    })
        except Exception as e:
            print(f"Error retrieving interfaces from Mininet for router {router_id}: {str(e)}")
        
        db_interfaces = router_config.get('interfaces', []) if router_config else []
        
        interfaces = []
        intf_names = set()
        
        for intf in mininet_interfaces:
            intf_names.add(intf['name'])
            interfaces.append(intf)
            
        for intf in db_interfaces:
            if intf.get('name') not in intf_names:
                intf_names.add(intf.get('name'))
                interfaces.append({
                    "name": intf.get('name'),
                    "ip": intf.get('ip'),
                    "subnet_mask": intf.get('subnet_mask', 24)
                })
                
        print(f"Router {router_id} interfaces: {interfaces}")
            
        return {
            "success": True,
            "interfaces": interfaces
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting router interfaces: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
