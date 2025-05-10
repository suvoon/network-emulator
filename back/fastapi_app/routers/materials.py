from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from django.contrib.auth.models import User
from django_app.models import StudentGroup, EducationalMaterial
from ..dependencies import get_current_active_user
from asgiref.sync import sync_to_async
from ..serializers import StudentGroupSerializer, EducationalMaterialSerializer
from rest_framework.renderers import JSONRenderer
import json
from fastapi import status
from datetime import datetime
from ..models import GroupBase, GroupDetail, GroupCreate, GroupUpdate, MaterialBase, MaterialCreate, MaterialUpdate

router = APIRouter(
    prefix="/api/materials",
    tags=["materials"],
)

@sync_to_async
def get_educational_materials(user: User = None, material_id: int = None, group_id: int = None, material_type: str = None):
    """Получение учебных материалов с фильтрацией по пользователю и правам доступа"""
    is_educator = user.profile.user_type == 'EDUCATOR'
    
    if material_id:
        try:
            material = EducationalMaterial.objects.get(id=material_id)
            if is_educator or material.author == user or material.is_public or user.profile.groups.filter(materials=material).exists():
                return material
            return None
        except EducationalMaterial.DoesNotExist:
            return None
    
    if is_educator:
        materials = EducationalMaterial.objects.all()
    else:
        materials = EducationalMaterial.objects.filter(
            is_public=True
        ).union(
            EducationalMaterial.objects.filter(groups__in=user.profile.groups.all())
        ).union(
            EducationalMaterial.objects.filter(author=user)
        )

    if group_id:
        materials = materials.filter(groups__id=group_id)
    
    if material_type:
        materials = materials.filter(material_type=material_type)
    
    return list(materials)

@sync_to_async
def create_educational_material(data: MaterialCreate, user: User):
    """Создание нового учебного материала"""
    if user.profile.user_type != 'EDUCATOR':
        return None, "Only educators can create materials"
        
    material = EducationalMaterial.objects.create(
        title=data.title,
        content=data.content,
        material_type=data.material_type,
        is_public=data.is_public,
        author=user
    )

    if data.group_ids:
        groups = StudentGroup.objects.filter(id__in=data.group_ids)
        material.groups.set(groups)
    
    return material, "Material created successfully"

@sync_to_async
def update_educational_material(material_id: int, data: MaterialUpdate, user: User):
    """Обновление учебного материала"""
    try:
        material = EducationalMaterial.objects.get(id=material_id)
        
        if user.profile.user_type != 'EDUCATOR' and material.author != user:
            return None, "You don't have permission to update this material"
            
        if data.title is not None:
            material.title = data.title
        if data.content is not None:
            material.content = data.content
        if data.material_type is not None:
            material.material_type = data.material_type
        if data.is_public is not None:
            material.is_public = data.is_public
            
        if data.group_ids is not None:
            groups = StudentGroup.objects.filter(id__in=data.group_ids)
            material.groups.set(groups)
            
        material.save()
        return material, "Material updated successfully"
    except EducationalMaterial.DoesNotExist:
        return None, "Material not found"

@sync_to_async
def delete_educational_material(material_id: int, user: User):
    """Удаление учебного материала"""
    try:
        material = EducationalMaterial.objects.get(id=material_id)
        
        if user.profile.user_type != 'EDUCATOR' and material.author != user:
            return False, "You don't have permission to delete this material"
            
        material.delete()
        return True, "Material deleted successfully"
    except EducationalMaterial.DoesNotExist:
        return False, "Material not found"

@sync_to_async
def format_material_for_response(material, include_groups=True):
    """Форматирование объекта материала для API-ответа"""
    if isinstance(material, list):
        result = []
        for m in material:
            response = {
                "id": m.id,
                "title": m.title,
                "content": m.content,
                "material_type": m.material_type,
                "author_name": m.author.username,
                "is_public": m.is_public,
                "created_at": m.created_at.isoformat(),
                "updated_at": m.updated_at.isoformat()
            }
            
            if include_groups:
                groups_data = []
                for group in m.groups.all():
                    groups_data.append({
                        "id": group.id,
                        "name": group.name,
                        "description": group.description
                    })
                response["groups"] = groups_data
            
            result.append(response)
        return result
        
    response = {
        "id": material.id,
        "title": material.title,
        "content": material.content,
        "material_type": material.material_type,
        "author_name": material.author.username,
        "is_public": material.is_public,
        "created_at": material.created_at.isoformat(),
        "updated_at": material.updated_at.isoformat()
    }
    
    if include_groups:
        groups_data = []
        for group in material.groups.all():
            groups_data.append({
                "id": group.id,
                "name": group.name,
                "description": group.description
            })
        response["groups"] = groups_data
        
    return response

@router.get("/")
async def list_materials(
    group_id: Optional[int] = Query(None, description="Filter by student group"),
    material_type: Optional[str] = Query(None, description="Filter by material type"),
    current_user: User = Depends(get_current_active_user)
):
    """Получение списка всех учебных материалов, доступных пользователю"""
    materials = await get_educational_materials(current_user, group_id=group_id, material_type=material_type)
    
    if not materials:
        return {"materials": []}
    
    formatted_materials = await format_material_for_response(materials)
    return {"materials": formatted_materials}

@router.post("/create/")
async def create_material(material: MaterialCreate, current_user: User = Depends(get_current_active_user)):
    """Создание нового учебного материала"""
    created_material, message = await create_educational_material(material, current_user)
    
    if not created_material:
        raise HTTPException(status_code=403, detail=message)
    
    formatted_material = await format_material_for_response(created_material)
    return {
        "success": True,
        "message": message,
        "material": formatted_material
    }

@router.get("/{material_id}/")
async def get_material(material_id: int, current_user: User = Depends(get_current_active_user)):
    """Получение конкретного учебного материала"""
    material = await get_educational_materials(current_user, material_id=material_id)
    
    if not material:
        raise HTTPException(status_code=404, detail="Material not found or you don't have access to it")
    
    formatted_material = await format_material_for_response(material)
    return {"material": formatted_material}

@router.put("/{material_id}/")
async def update_material(
    material_id: int,
    material_data: MaterialUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Обновление учебного материала"""
    updated_material, message = await update_educational_material(material_id, material_data, current_user)
    
    if not updated_material:
        status_code = 404 if "not found" in message else 403
        raise HTTPException(status_code=status_code, detail=message)
    
    return {"success": True, "message": message}

@router.delete("/{material_id}/")
async def delete_material(material_id: int, current_user: User = Depends(get_current_active_user)):
    """Удаление учебного материала"""
    success, message = await delete_educational_material(material_id, current_user)
    
    if not success:
        status_code = 404 if "not found" in message else 403
        raise HTTPException(status_code=status_code, detail=message)
    
    return {"success": True, "message": message}