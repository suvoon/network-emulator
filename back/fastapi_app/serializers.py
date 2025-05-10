from rest_framework import serializers
from django.contrib.auth.models import User
from django_app.models import NetworkTopology, StudentGroup, EducationalMaterial

class UserSerializer(serializers.ModelSerializer):
    user_type = serializers.SerializerMethodField()
    
    def get_user_type(self, obj):
        return 'EDUCATOR' if obj.is_staff else 'STUDENT'
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'user_type']

class NetworkTopologySerializer(serializers.ModelSerializer):
    class Meta:
        model = NetworkTopology
        fields = ['id', 'name', 'description', 'created_at', 'is_active', 'user']
        
class StudentGroupSerializer(serializers.ModelSerializer):
    students = UserSerializer(many=True, read_only=True)
    student_count = serializers.SerializerMethodField()
    
    def get_student_count(self, obj):
        return obj.students.count()
    
    class Meta:
        model = StudentGroup
        fields = ['id', 'name', 'description', 'created_at', 'updated_at', 'students', 'student_count']

class EducationalMaterialSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    groups = StudentGroupSerializer(many=True, read_only=True)
    
    def get_author_name(self, obj):
        return f"{obj.author.first_name} {obj.author.last_name}".strip() or obj.author.username
    
    class Meta:
        model = EducationalMaterial
        fields = ['id', 'title', 'content', 'material_type', 'created_at', 'updated_at', 
                 'author', 'author_name', 'groups', 'is_public'] 