const API_URL = process.env.NEXT_PUBLIC_API_HOST || 'http://localhost:8000';
export { API_URL };

interface Group {
    id: number;
    name: string;
    description?: string;
    student_count?: number;
    members?: Array<{ id: number, username: string, email: string }>;
}

interface Material {
    id: number;
    title: string;
    content: string;
    material_type: string;
    author_name: string;
    is_public: boolean;
    created_at: string;
    updated_at: string;
    groups?: Group[];
}

export async function fetchWithAuth(endpoint: string, options: RequestInit = {}) {
    const token = localStorage.getItem('token');

    const requestOptions: RequestInit = {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` }),
            ...options.headers,
        },
        credentials: 'include',
    };

    const response = await fetch(`${API_URL}${endpoint}`, requestOptions);

    if (response.status === 401) {
        console.error('Authentication required. Please log in.');
        throw new Error('Authentication required. Please log in to continue.');
    }

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
}


export async function fetchWithDjangoAuth(endpoint: string, options: RequestInit = {}) {
    const token = localStorage.getItem('token');

    if (!token) {
        if (typeof window !== 'undefined') {
            window.location.href = '/auth/login';
        }
        throw new Error('Authentication required. Please log in to continue.');
    }

    const requestOptions: RequestInit = {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
            ...options.headers,
        },
        credentials: 'include',
    };

    const url = `${API_URL}${endpoint}`;

    try {
        const response = await fetch(url, requestOptions);

        if (response.status === 401) {
            console.error('Authentication required. Please log in.');
            localStorage.removeItem('token');
            localStorage.removeItem('userId');
            localStorage.removeItem('username');
            localStorage.removeItem('userType');

            if (typeof window !== 'undefined') {
                window.location.href = '/auth/login';
            }

            throw new Error('Authentication required. Please log in to continue.');
        }

        if (!response.ok) {
            const errorText = await response.text();
            let errorMessage: string;

            try {
                const errorData = JSON.parse(errorText);
                errorMessage = errorData.error || errorData.detail || `API Error: ${response.status} ${response.statusText}`;
            } catch {
                errorMessage = errorText || `API Error: ${response.status} ${response.statusText}`;
            }

            throw new Error(errorMessage);
        }

        if (response.status === 204) {
            return {};
        }

        const text = await response.text();
        return text ? JSON.parse(text) : {};
    } catch (error) {
        console.error('Error in fetchWithDjangoAuth:', error);
        throw error;
    }
}

export const topologyApi = {
    list: () => fetchWithAuth('/api/network/topology/list'),

    get: (id: number) => fetchWithAuth(`/api/network/topology/${id}`),

    create: (data: any) => fetchWithAuth('/api/network/topology/create', {
        method: 'POST',
        body: JSON.stringify(data),
    }),

    activate: (id: number) => fetchWithAuth(`/api/network/topology/${id}/activate`, {
        method: 'POST',
    }),

    delete: (id: number) => fetchWithAuth(`/api/network/topology/${id}`, {
        method: 'DELETE',
    }),

    validate: () => fetchWithAuth('/api/network/topology-validate'),
};

export const nodeApi = {
    addHost: (data: any) => fetchWithAuth('/api/network/node/host', {
        method: 'POST',
        body: JSON.stringify(data),
    }),

    addSwitch: (data: any) => fetchWithAuth('/api/network/node/switch', {
        method: 'POST',
        body: JSON.stringify(data),
    }),

    addRouter: (data: any) => fetchWithAuth('/api/network/node/router', {
        method: 'POST',
        body: JSON.stringify(data),
    }),

    deleteHost: (hostId: string) => fetchWithAuth(`/api/network/node/host/${hostId}`, {
        method: 'DELETE',
    }),

    deleteSwitch: (switchId: string) => fetchWithAuth(`/api/network/node/switch/${switchId}`, {
        method: 'DELETE',
    }),

    deleteRouter: (routerId: string) => fetchWithAuth(`/api/network/node/router/${routerId}`, {
        method: 'DELETE',
    }),

    updatePosition: (data: any) => fetchWithAuth('/api/network/node/position', {
        method: 'PUT',
        body: JSON.stringify(data),
    }),

    updateDisplayName: (data: any) => fetchWithAuth('/api/network/node/display-name', {
        method: 'PUT',
        body: JSON.stringify(data),
    }),

    updateHostIp: (data: any) => fetchWithAuth('/api/network/node/host/ip', {
        method: 'PUT',
        body: JSON.stringify(data),
    }),

    updateSwitchIp: (data: any) => fetchWithAuth('/api/network/node/switch/ip', {
        method: 'PUT',
        body: JSON.stringify(data),
    }),

    updateRouterIp: (data: any) => fetchWithAuth('/api/network/node/router/ip', {
        method: 'PUT',
        body: JSON.stringify(data),
    }),

    configureRouterInterface: (data: any) => fetchWithAuth('/api/network/node/router/interface', {
        method: 'POST',
        body: JSON.stringify(data),
    }),

    getRouterInterfaces: (routerId: string) => fetchWithAuth(`/api/network/node/router/${routerId}/interfaces`, {
        method: 'GET',
    }),
};

export const linkApi = {
    add: (data: any) => fetchWithAuth('/api/network/link', {
        method: 'POST',
        body: JSON.stringify(data),
    }),

    delete: (data: any) => fetchWithAuth('/api/network/link', {
        method: 'DELETE',
        body: JSON.stringify(data),
    }),
};

export const packetApi = {
    startTrace: (data: any) => fetchWithAuth('/api/network/packet/trace/start', {
        method: 'POST',
        body: JSON.stringify(data),
    }),

    getTrace: (traceId: number) => fetchWithAuth(`/api/network/packet/trace/${traceId}`),

    ping: (data: any) => fetchWithAuth('/api/network/packet/ping', {
        method: 'POST',
        body: JSON.stringify(data),
    }),

    tcpConnect: (data: any) => fetchWithAuth('/api/network/packet/tcp', {
        method: 'POST',
        body: JSON.stringify(data),
    }),

    udpSend: (data: any) => fetchWithAuth('/api/network/packet/udp', {
        method: 'POST',
        body: JSON.stringify(data),
    }),

    httpRequest: (data: any) => fetchWithAuth('/api/network/packet/http', {
        method: 'POST',
        body: JSON.stringify(data),
    }),
};

export const materialsApi = {
    getStudentGroups: async () => {
        const response = await fetchWithDjangoAuth('/api/groups/');
        return response.groups || [];
    },

    getStudentGroup: async (groupId: number) => {
        const response = await fetchWithDjangoAuth(`/api/groups/${groupId}/`);
        return response.group || null;
    },

    createStudentGroup: async (data: { name: string, description?: string }) => {
        const response = await fetchWithDjangoAuth('/api/groups/create/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        return response;
    },

    updateStudentGroup: async (groupId: number, data: { name?: string, description?: string }) => {
        const response = await fetchWithDjangoAuth(`/api/groups/${groupId}/`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
        return response;
    },

    deleteStudentGroup: async (groupId: number) => {
        const response = await fetchWithDjangoAuth(`/api/groups/${groupId}/`, {
            method: 'DELETE',
        });
        return response;
    },

    addStudentToGroup: async (groupId: number, studentId: number) => {
        const response = await fetchWithDjangoAuth(`/api/groups/${groupId}/members/`, {
            method: 'POST',
            body: JSON.stringify({ student_id: studentId, action: 'add' })
        });
        return response;
    },

    removeStudentFromGroup: async (groupId: number, studentId: number) => {
        const response = await fetchWithDjangoAuth(`/api/groups/${groupId}/members/`, {
            method: 'POST',
            body: JSON.stringify({ student_id: studentId, action: 'remove' })
        });
        return response;
    },

    getMaterials: async (groupId?: number, materialType?: string) => {
        const response = await fetchWithDjangoAuth('/api/materials/');
        let materials = response.materials || [] as Material[];

        if (groupId || materialType) {
            materials = materials.filter((material: Material) => {
                if (groupId && material.groups) {
                    const groupMatch = material.groups.some((group: Group) => group.id === groupId);
                    if (!groupMatch) return false;
                }

                if (materialType && material.material_type !== materialType) {
                    return false;
                }

                return true;
            });
        }

        return materials;
    },

    getMaterial: async (materialId: number) => {
        const response = await fetchWithDjangoAuth(`/api/materials/${materialId}/`);
        return response.material || null;
    },

    createMaterial: async (data: {
        title: string,
        content: string,
        material_type: string,
        is_public?: boolean,
        group_ids?: number[]
    }) => {
        const payload = {
            title: data.title,
            content: data.content,
            material_type: data.material_type,
            is_public: data.is_public || false,
            group_ids: data.group_ids || []
        };

        const response = await fetchWithDjangoAuth('/api/materials/create/', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        return response;
    },

    updateMaterial: async (materialId: number, data: {
        title?: string,
        content?: string,
        material_type?: string,
        is_public?: boolean,
        group_ids?: number[]
    }) => {
        const payload: any = {};

        if (data.title !== undefined) payload.title = data.title;
        if (data.content !== undefined) payload.content = data.content;
        if (data.material_type !== undefined) payload.material_type = data.material_type;
        if (data.is_public !== undefined) payload.is_public = data.is_public;
        if (data.group_ids !== undefined) payload.groups = data.group_ids;

        const response = await fetchWithDjangoAuth(`/api/materials/${materialId}/`, {
            method: 'PUT',
            body: JSON.stringify(payload)
        });
        return response;
    },

    deleteMaterial: async (materialId: number) => {
        const response = await fetchWithDjangoAuth(`/api/materials/${materialId}/`, {
            method: 'DELETE',
        });
        return response;
    },
};

export const authApi = {
    login: async (username: string, password: string) => {
        const response = await fetch(`${API_URL}/api/auth/login/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({ username, password }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || 'Failed to login');
        }

        const data = await response.json();

        if (!data.token) {
            console.error('No token returned from login endpoint');
            throw new Error('Authentication error: No token provided by server');
        }

        if (!data.user) {
            console.error('No user data returned from login endpoint');
            throw new Error('Authentication error: No user data provided by server');
        }

        if (!data.user.id || !data.user.username || !data.user.user_type) {
            console.error('Incomplete user data returned from login endpoint', data.user);
            throw new Error('Authentication error: Incomplete user data provided by server');
        }

        return data;
    },

    logout: () => {
        fetch(`${API_URL}/api/auth/logout/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            credentials: 'include',
        });

        localStorage.removeItem('token');
        localStorage.removeItem('userId');
        localStorage.removeItem('isStaff');
        localStorage.removeItem('username');
        localStorage.removeItem('userType');
    },

    getProfile: async () => {
        return fetchWithAuth('/api/auth/user/');
    },

    getUsers: async () => {
        const response = await fetchWithDjangoAuth('/api/auth/users');
        if (!response.users) {
            return [];
        }
        return response.users;
    },
}; 