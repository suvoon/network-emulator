const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface Group {
    id: number;
    name: string;
    description: string;
    created_at: string;
    member_count: number;
}

export interface GroupDetail extends Group {
    members: {
        id: number;
        username: string;
        email: string;
    }[];
}

export async function getGroups() {
    const response = await fetch(`${API_URL}/api/groups/`, {
        credentials: 'include',
    });

    if (!response.ok) {
        throw new Error('Failed to fetch groups');
    }

    const data = await response.json();
    return data.groups;
}

export async function getGroup(id: number): Promise<GroupDetail> {
    const response = await fetch(`${API_URL}/api/groups/${id}/`, {
        credentials: 'include',
    });

    if (!response.ok) {
        throw new Error('Failed to fetch group');
    }

    const data = await response.json();
    return data.group;
}

export async function createGroup(groupData: {
    name: string;
    description?: string;
}): Promise<number> {
    const response = await fetch(`${API_URL}/api/groups/create/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(groupData),
        credentials: 'include',
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to create group');
    }

    const data = await response.json();
    return data.group_id;
}

export async function updateGroup(
    id: number,
    groupData: {
        name?: string;
        description?: string;
    }
): Promise<void> {
    const response = await fetch(`${API_URL}/api/groups/${id}/`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(groupData),
        credentials: 'include',
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update group');
    }
}

export async function deleteGroup(id: number): Promise<void> {
    const response = await fetch(`${API_URL}/api/groups/${id}/`, {
        method: 'DELETE',
        credentials: 'include',
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to delete group');
    }
}

export async function addMemberToGroup(groupId: number, username: string): Promise<void> {
    const response = await fetch(`${API_URL}/api/groups/${groupId}/members/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            username,
            action: 'add'
        }),
        credentials: 'include',
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to add member to group');
    }
}

export async function removeMemberFromGroup(groupId: number, username: string): Promise<void> {
    const response = await fetch(`${API_URL}/api/groups/${groupId}/members/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            username,
            action: 'remove'
        }),
        credentials: 'include',
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to remove member from group');
    }
} 