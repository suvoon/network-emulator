from django.db import models
import json
from django.contrib.auth.models import User

class NetworkTopology(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    hosts = models.JSONField()
    switches = models.JSONField()
    links = models.JSONField()
    routers = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='topologies', null=True)

    def __str__(self):
        return self.name

    def get_topology_config(self):
        routers = self.routers or []
        
        return {
            'name': self.name,
            'description': self.description,
            'hosts': [
                {
                    'name': host['name'],
                    'display_name': host.get('display_name', host['name']),
                    'ip': host.get('ip'),
                    'x': host.get('x', 100),
                    'y': host.get('y', 100),
                }
                for host in self.hosts
            ],
            'switches': [
                {
                    'name': switch['name'],
                    'display_name': switch.get('display_name', switch['name']),
                    'x': switch.get('x', 200),
                    'y': switch.get('y', 200),
                }
                for switch in self.switches
            ],
            'routers': [
                {
                    'name': router['name'],
                    'display_name': router.get('display_name', router['name']),
                    'ip': router.get('ip'),
                    'x': router.get('x', 300),
                    'y': router.get('y', 300),
                    'interfaces': router.get('interfaces', []),
                    'routes': router.get('routes', [])
                }
                for router in routers
            ],
            'links': self.links
        }

class NetworkNode(models.Model):
    NODE_TYPES = (
        ('host', 'Host'),
        ('switch', 'Switch'),
    )
    
    topology = models.ForeignKey(NetworkTopology, on_delete=models.CASCADE, related_name='nodes')
    name = models.CharField(max_length=200)
    node_type = models.CharField(max_length=10, choices=NODE_TYPES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('topology', 'name')

    def __str__(self):
        return f"{self.name} ({self.node_type})"

class PacketTrace(models.Model):
    PACKET_STATES = (
        ('created', 'Created'),
        ('sending', 'Sending'),
        ('received', 'Received'),
        ('dropped', 'Dropped'),
        ('completed', 'Completed'),
    )

    topology = models.ForeignKey(NetworkTopology, on_delete=models.CASCADE, related_name='packet_traces')
    source_node = models.CharField(max_length=200)
    destination_node = models.CharField(max_length=200)
    packet_config = models.JSONField()
    route = models.JSONField(default=list)
    state = models.CharField(max_length=20, choices=PACKET_STATES, default='created')
    current_node = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Packet {self.id}: {self.source_node} -> {self.destination_node}"

class StudentGroup(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    students = models.ManyToManyField(User, related_name='student_groups', blank=True)

    def __str__(self):
        return self.name

class EducationalMaterial(models.Model):
    MATERIAL_TYPES = (
        ('text', 'Text'),
        ('video', 'Video'),
        ('quiz', 'Quiz'),
        ('assignment', 'Assignment'),
        ('simulation', 'Simulation'),
    )
    
    title = models.CharField(max_length=255)
    content = models.TextField()
    material_type = models.CharField(max_length=20, choices=MATERIAL_TYPES, default='text')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='materials')
    groups = models.ManyToManyField(StudentGroup, related_name='materials', blank=True)
    is_public = models.BooleanField(default=False)
    
    def __str__(self):
        return self.title

class UserProfile(models.Model):
    USER_TYPE_CHOICES = (
        ('STUDENT', 'Student'),
        ('EDUCATOR', 'Educator'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='STUDENT')
    groups = models.ManyToManyField(StudentGroup, related_name='members', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} ({self.get_user_type_display()})"
