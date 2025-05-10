const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface Material {
    id: number;
    title: string;
    content: string;
    author: string;
    created_at: string;
    updated_at: string;
    groups: Group[];
}

export interface Group {
    id: number;
    name: string;
}

export async function getMaterials() {
    const response = await fetch(`${API_URL}/api/materials/`, {
        credentials: 'include',
    });

    if (!response.ok) {
        throw new Error('Failed to fetch materials');
    }

    const data = await response.json();
    return data.materials;
}

export async function getMaterial(id: number): Promise<Material> {
    const response = await fetch(`${API_URL}/api/materials/${id}/`, {
        credentials: 'include',
    });

    if (!response.ok) {
        throw new Error('Failed to fetch material');
    }

    const data = await response.json();
    return data.material;
}

export async function createMaterial(materialData: {
    title: string;
    content: string;
    groups?: number[];
}): Promise<number> {
    const response = await fetch(`${API_URL}/api/materials/create/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(materialData),
        credentials: 'include',
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to create material');
    }

    const data = await response.json();
    return data.material_id;
}

export async function updateMaterial(
    id: number,
    materialData: {
        title?: string;
        content?: string;
        groups?: number[];
    }
): Promise<void> {
    const response = await fetch(`${API_URL}/api/materials/${id}/`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(materialData),
        credentials: 'include',
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update material');
    }
}

export async function deleteMaterial(id: number): Promise<void> {
    const response = await fetch(`${API_URL}/api/materials/${id}/`, {
        method: 'DELETE',
        credentials: 'include',
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to delete material');
    }
} 