from django.contrib import admin
from .models import NetworkTopology, NetworkNode, PacketTrace, UserProfile, StudentGroup, EducationalMaterial

@admin.register(NetworkTopology)
class NetworkTopologyAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at', 'updated_at', 'is_active')
    search_fields = ('name', 'description', 'user__username')
    list_filter = ('is_active', 'created_at', 'user')

@admin.register(NetworkNode)
class NetworkNodeAdmin(admin.ModelAdmin):
    list_display = ('name', 'node_type', 'topology', 'ip_address')
    list_filter = ('node_type', 'topology')
    search_fields = ('name', 'ip_address')

@admin.register(PacketTrace)
class PacketTraceAdmin(admin.ModelAdmin):
    list_display = ('id', 'topology', 'source_node', 'destination_node', 'state', 'created_at')
    list_filter = ('state', 'created_at')
    search_fields = ('source_node', 'destination_node')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_type', 'created_at')
    list_filter = ('user_type', 'created_at')
    search_fields = ('user__username', 'user__email')
    filter_horizontal = ('groups',)

@admin.register(StudentGroup)
class StudentGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at', 'student_count')
    search_fields = ('name', 'description')
    filter_horizontal = ('students',)
    
    def student_count(self, obj):
        return obj.students.count()
    student_count.short_description = 'Number of Students'

@admin.register(EducationalMaterial)
class EducationalMaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'material_type', 'author', 'is_public', 'created_at')
    list_filter = ('material_type', 'is_public', 'author')
    search_fields = ('title', 'content')
    filter_horizontal = ('groups',)
