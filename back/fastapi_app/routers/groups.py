from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from ..models import GroupBase, GroupDetail, GroupCreate, GroupUpdate
from django.contrib.auth.models import User
from django_app.models import StudentGroup
from asgiref.sync import sync_to_async
from ..dependencies import get_current_active_user

router = APIRouter(
    prefix="/api/groups",
    tags=["groups"],
)

@sync_to_async
def get_groups_for_user(user: User):
    """Получение групп для текущего пользователя"""
    if user.profile.user_type == 'EDUCATOR':
        groups = list(StudentGroup.objects.all())
    else:
        groups = list(user.profile.groups.all())
        
    return groups

@sync_to_async
def get_group_by_id(group_id: int, user: User):
    """Получение конкретной группы с проверкой прав пользователя"""
    try:
        if user.profile.user_type == 'EDUCATOR':
            return StudentGroup.objects.get(id=group_id)
        else:
            return user.profile.groups.get(id=group_id)
    except StudentGroup.DoesNotExist:
        return None

@sync_to_async
def create_new_group(group: GroupCreate, user: User):
    """Создание новой группы"""
    if user.profile.user_type != 'EDUCATOR':
        return None, "Only educators can create groups"
        
    new_group = StudentGroup.objects.create(
        name=group.name,
        description=group.description or "",
    )
    return new_group, "Group created successfully"

@sync_to_async
def update_existing_group(group_id: int, group_data: GroupUpdate, user: User):
    """Обновление существующей группы"""
    if user.profile.user_type != 'EDUCATOR':
        return None, "Only educators can update groups"
        
    try:
        group = StudentGroup.objects.get(id=group_id)
        
        if group_data.name is not None:
            group.name = group_data.name
        if group_data.description is not None:
            group.description = group_data.description
            
        group.save()
        return group, "Группа успешно обновлена"
    except StudentGroup.DoesNotExist:
        return None, "Группа не найдена"

@sync_to_async
def delete_existing_group(group_id: int, user: User):
    """Удаление группы"""
    if user.profile.user_type != 'EDUCATOR':
        return False, "Only educators can delete groups"
        
    try:
        group = StudentGroup.objects.get(id=group_id)
        group.delete()
        return True, "Группа успешно удалена"
    except StudentGroup.DoesNotExist:
        return False, "Группа не найдена"

@sync_to_async
def manage_group_member(group_id: int, data: dict, user: User):
    """Добавление или удаление студента из группы"""
    if user.profile.user_type != 'EDUCATOR':
        return None, "Only educators can manage group members"
        
    student_id = data.get("student_id")
    action = data.get("action")
    
    if not student_id or action not in ["add", "remove"]:
        return None, "Invalid request data"
        
    try:
        group = StudentGroup.objects.get(id=group_id)
        student = User.objects.get(id=student_id)
        
        if action == "add":
            student.profile.groups.add(group)
            return group, f"Студент успешно добавлен"
        elif action == "remove":
            student.profile.groups.remove(group)
            return group, f"Студент успешно удален"
    except StudentGroup.DoesNotExist:
        return None, "Группа не найдена"
    except User.DoesNotExist:
        return None, "Студент не найден"

@sync_to_async
def format_group_for_response(group):
    """Форматирование группы с её участниками для ответа"""
    members = list(group.members.all())
    
    formatted_members = []
    for member in members:
        formatted_members.append({
            "id": member.user.id,
            "username": member.user.username,
            "email": member.user.email
        })
    
    formatted_group = {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "student_count": len(members),
        "members": formatted_members
    }
    
    return formatted_group

@router.get("/")
async def get_groups(current_user: User = Depends(get_current_active_user)):
    """Получение всех групп, доступных пользователю"""
    groups = await get_groups_for_user(current_user)
    
    formatted_groups = []
    for group in groups:
        formatted_group = await format_group_for_response(group)
        formatted_groups.append(formatted_group)
        
    return {"groups": formatted_groups}

@router.get("/{group_id}/")
async def get_group(group_id: int, current_user: User = Depends(get_current_active_user)):
    """Получение конкретной группы по ID"""
    group = await get_group_by_id(group_id, current_user)
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
        
    formatted_group = await format_group_for_response(group)
        
    return {"group": formatted_group}

@router.post("/create/")
async def create_group(group: GroupCreate, current_user: User = Depends(get_current_active_user)):
    """Создание новой группы"""
    created_group, message = await create_new_group(group, current_user)
    
    if not created_group:
        raise HTTPException(status_code=403, detail=message)
    
    formatted_group = await format_group_for_response(created_group)
        
    return {
        "success": True, 
        "message": message, 
        "group": formatted_group
    }

@router.put("/{group_id}/")
async def update_group(group_id: int, group_data: GroupUpdate, current_user: User = Depends(get_current_active_user)):
    """Обновление существующей группы"""
    updated_group, message = await update_existing_group(group_id, group_data, current_user)
    
    if not updated_group:
        status_code = 403 if "Only educators" in message else 404
        raise HTTPException(status_code=status_code, detail=message)
        
    return {"success": True, "message": message}

@router.delete("/{group_id}/")
async def delete_group(group_id: int, current_user: User = Depends(get_current_active_user)):
    """Удаление группы"""
    success, message = await delete_existing_group(group_id, current_user)
    
    if not success:
        status_code = 403 if "Only educators" in message else 404
        raise HTTPException(status_code=status_code, detail=message)
        
    return {"success": True, "message": message}

@router.post("/{group_id}/members/")
async def manage_group_members(group_id: int, data: dict, current_user: User = Depends(get_current_active_user)):
    """Добавление или удаление студента из группы"""
    result, message = await manage_group_member(group_id, data, current_user)
    
    if not result:
        status_code = 403 if "Only educators" in message else 404
        if "Invalid request data" in message:
            status_code = 400
        raise HTTPException(status_code=status_code, detail=message)
        
    return {"success": True, "message": message} 