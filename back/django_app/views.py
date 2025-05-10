from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from .models import UserProfile, StudentGroup, EducationalMaterial
import json
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.tokens import RefreshToken
import jwt
from django.conf import settings

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

@csrf_exempt
def register_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        user_type = data.get('user_type', 'STUDENT')
        
        if not username or not email or not password:
            return JsonResponse({'error': 'Все поля обязательны для заполнения'}, status=400)
        
        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Пользователь с таким именем уже существует'}, status=400)
        
        if User.objects.filter(email=email).exists():
            return JsonResponse({'error': 'Пользователь с такой электронной почтой уже существует'}, status=400)
        
        if user_type not in ['STUDENT', 'EDUCATOR']:
            user_type = 'STUDENT'
        
        user = User.objects.create_user(username=username, email=email, password=password)
        UserProfile.objects.create(user=user, user_type=user_type)
        
        tokens = get_tokens_for_user(user)
        
        return JsonResponse({
            'message': 'Пользователь успешно зарегистрирован',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'user_type': user.profile.user_type
            },
            'token': tokens['access']
        })
    
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)

@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return JsonResponse({'error': 'Имя пользователя и пароль обязательны'}, status=400)
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            tokens = get_tokens_for_user(user)
            
            return JsonResponse({
                'message': 'Вход выполнен успешно',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'user_type': user.profile.user_type
                },
                'token': tokens['access']
            })
        else:
            return JsonResponse({'error': 'Неверные учетные данные'}, status=401)
    
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)

@csrf_exempt
def logout_view(request):
    if request.method == 'POST':
        return JsonResponse({'message': 'Выход выполнен успешно'})
    
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)

@csrf_exempt
def current_user_view(request):
    if request.method == 'GET':
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Не авторизован'}, status=401)
        
        token = auth_header.replace('Bearer ', '')
        
        try:
            payload = jwt.decode(
                token,
                settings.SIMPLE_JWT['SIGNING_KEY'],
                algorithms=[settings.SIMPLE_JWT['ALGORITHM']]
            )
            
            user_id = payload.get('user_id')
            if not user_id:
                return JsonResponse({'error': 'Недействительный токен'}, status=401)
            
            try:
                user = User.objects.get(id=user_id)
                
                return JsonResponse({
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'user_type': user.profile.user_type
                    }
                })
            except User.DoesNotExist:
                return JsonResponse({'error': 'Пользователь не найден'}, status=401)
                
        except Exception as e:
            print(f"Token verification error: {str(e)}")
            return JsonResponse({'error': 'Недействительный токен'}, status=401)
    
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)

@login_required
def list_materials(request):
    if request.method == 'GET':
        user = request.user
        
        if user.profile.user_type == 'EDUCATOR':
            materials = EducationalMaterial.objects.filter(author=user)
        else:
            user_groups = user.profile.groups.all()
            materials = EducationalMaterial.objects.filter(
                Q(groups__in=user_groups) | Q(groups__isnull=True)
            ).distinct()
        
        materials_data = [{
            'id': material.id,
            'title': material.title,
            'author': material.author.username,
            'created_at': material.created_at.isoformat(),
            'updated_at': material.updated_at.isoformat()
        } for material in materials]
        
        return JsonResponse({'materials': materials_data})
    
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)

@login_required
def material_detail(request, material_id):
    material = get_object_or_404(EducationalMaterial, id=material_id)
    user = request.user
    
    if user.profile.user_type == 'EDUCATOR' and material.author != user:
        return JsonResponse({'error': 'У вас нет доступа к этому материалу'}, status=403)
    
    if user.profile.user_type == 'STUDENT':
        user_groups = user.profile.groups.all()
        if not material.groups.filter(id__in=[g.id for g in user_groups]).exists() and material.groups.exists():
            return JsonResponse({'error': 'У вас нет доступа к этому материалу'}, status=403)
    
    if request.method == 'GET':
        material_data = {
            'id': material.id,
            'title': material.title,
            'content': material.content,
            'author': material.author.username,
            'created_at': material.created_at.isoformat(),
            'updated_at': material.updated_at.isoformat(),
            'groups': [{'id': g.id, 'name': g.name} for g in material.groups.all()]
        }
        
        return JsonResponse({'material': material_data})
    
    elif request.method == 'PUT' and user.profile.user_type == 'EDUCATOR' and material.author == user:
        data = json.loads(request.body)
        material.title = data.get('title', material.title)
        material.content = data.get('content', material.content)
        
        if 'groups' in data:
            group_ids = data.get('groups', [])
            material.groups.clear()
            for group_id in group_ids:
                try:
                    group = StudentGroup.objects.get(id=group_id, created_by=user)
                    material.groups.add(group)
                except StudentGroup.DoesNotExist:
                    pass
        
        material.save()
        return JsonResponse({'message': 'Материал обновлен успешно'})
    
    elif request.method == 'DELETE' and user.profile.user_type == 'EDUCATOR' and material.author == user:
        material.delete()
        return JsonResponse({'message': 'Материал удален успешно'})
    
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)

@login_required
@csrf_exempt
def create_material(request):
    if request.method == 'POST' and request.user.profile.user_type == 'EDUCATOR':
        data = json.loads(request.body)
        title = data.get('title')
        content = data.get('content')
        
        if not title or not content:
            return JsonResponse({'error': 'Необходимо указать заголовок и содержание'}, status=400)
        
        material = EducationalMaterial.objects.create(
            title=title,
            content=content,
            author=request.user
        )
        
        group_ids = data.get('groups', [])
        for group_id in group_ids:
            try:
                group = StudentGroup.objects.get(id=group_id, created_by=request.user)
                material.groups.add(group)
            except StudentGroup.DoesNotExist:
                pass
        
        return JsonResponse({
            'message': 'Материал создан успешно',
            'material_id': material.id
        })
    
    return JsonResponse({'error': 'Метод не разрешен или недостаточно прав'}, status=405)

@login_required
def list_groups(request):
    if request.method == 'GET':
        user = request.user
        
        if user.profile.user_type == 'EDUCATOR':
            groups = StudentGroup.objects.filter(created_by=user)
        else:
            groups = user.profile.groups.all()
        
        groups_data = [{
            'id': group.id,
            'name': group.name,
            'description': group.description,
            'created_at': group.created_at.isoformat(),
            'member_count': group.members.count()
        } for group in groups]
        
        return JsonResponse({'groups': groups_data})
    
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)

@login_required
@csrf_exempt
def create_group(request):
    if request.method == 'POST' and request.user.profile.user_type == 'EDUCATOR':
        data = json.loads(request.body)
        name = data.get('name')
        description = data.get('description', '')
        
        if not name:
            return JsonResponse({'error': 'Необходимо указать название группы'}, status=400)
        
        group = StudentGroup.objects.create(
            name=name,
            description=description,
            created_by=request.user
        )
        
        return JsonResponse({
            'message': 'Группа создана успешно',
            'group_id': group.id
        })
    
    return JsonResponse({'error': 'Метод не разрешен или недостаточно прав'}, status=405)

@login_required
def group_detail(request, group_id):
    user = request.user
    
    if user.profile.user_type == 'EDUCATOR':
        group = get_object_or_404(StudentGroup, id=group_id, created_by=user)
    else:
        group = get_object_or_404(StudentGroup, id=group_id, members=user.profile)
    
    if request.method == 'GET':
        members = [{
            'id': member.user.id,
            'username': member.user.username,
            'email': member.user.email
        } for member in group.members.all()]
        
        group_data = {
            'id': group.id,
            'name': group.name,
            'description': group.description,
            'created_at': group.created_at.isoformat(),
            'members': members
        }
        
        return JsonResponse({'group': group_data})
    
    elif request.method == 'PUT' and user.profile.user_type == 'EDUCATOR':
        data = json.loads(request.body)
        group.name = data.get('name', group.name)
        group.description = data.get('description', group.description)
        group.save()
        
        return JsonResponse({'message': 'Группа обновлена успешно'})
    
    elif request.method == 'DELETE' and user.profile.user_type == 'EDUCATOR':
        group.delete()
        return JsonResponse({'message': 'Группа удалена успешно'})
    
    return JsonResponse({'error': 'Метод не разрешен или недостаточно прав'}, status=405)

@login_required
@csrf_exempt
def manage_group_members(request, group_id):
    user = request.user
    
    if user.profile.user_type != 'EDUCATOR':
        return JsonResponse({'error': 'Недостаточно прав'}, status=403)
    
    group = get_object_or_404(StudentGroup, id=group_id, created_by=user)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username')
        action = data.get('action')
        
        if not username or not action:
            return JsonResponse({'error': 'Необходимо указать имя пользователя и действие'}, status=400)
        
        try:
            student = User.objects.get(username=username)
            if student.profile.user_type != 'STUDENT':
                return JsonResponse({'error': 'Пользователь не является студентом'}, status=400)
            
            if action == 'add':
                group.members.add(student.profile)
                return JsonResponse({'message': 'Студент добавлен в группу'})
            elif action == 'remove':
                group.members.remove(student.profile)
                return JsonResponse({'message': 'Студент удален из группы'})
            else:
                return JsonResponse({'error': 'Неизвестное действие'}, status=400)
        except User.DoesNotExist:
            return JsonResponse({'error': 'Пользователь не найден'}, status=404)
    
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)

@csrf_exempt
def users_list_view(request):
    """Вывод списка всех пользователей для преподавателей"""
    if request.method == 'GET':
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Не авторизован'}, status=401)
        
        token = auth_header.replace('Bearer ', '')
        
        try:
            payload = jwt.decode(
                token,
                settings.SIMPLE_JWT['SIGNING_KEY'],
                algorithms=[settings.SIMPLE_JWT['ALGORITHM']]
            )
            
            user_id = payload.get('user_id')
            if not user_id:
                return JsonResponse({'error': 'Недействительный токен'}, status=401)
            
            try:
                user = User.objects.get(id=user_id)
                
                if user.profile.user_type != 'EDUCATOR':
                    return JsonResponse({'error': 'У вас нет доступа к этому ресурсу'}, status=403)
                
                users = User.objects.select_related('profile').all()
                
                users_data = [{
                    'id': u.id,
                    'username': u.username,
                    'email': u.email,
                    'user_type': u.profile.user_type,
                } for u in users]
                
                return JsonResponse({'users': users_data})
                
            except User.DoesNotExist:
                return JsonResponse({'error': 'Пользователь не найден'}, status=401)
                
        except Exception as e:
            print(f"Token verification error: {str(e)}")
            return JsonResponse({'error': 'Недействительный токен'}, status=401)
    
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)
