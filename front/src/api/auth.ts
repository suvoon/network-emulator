import { API_URL, fetchWithDjangoAuth } from './network';

export interface User {
    id: number;
    username: string;
    email: string;
    user_type: string;
}

export interface RegisterData {
    username: string;
    email: string;
    password: string;
    user_type: string;
}

export interface LoginData {
    username: string;
    password: string;
}

export interface AuthResponse {
    message: string;
    user: User;
    token?: string;
}

export async function register(data: RegisterData): Promise<User> {
    const response = await fetch(`${API_URL}/api/auth/register/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Registration failed');
    }

    const responseData = await response.json() as AuthResponse;

    if (!responseData.token) {
        console.error('No token returned from register endpoint');
        throw new Error('Authentication error: No token provided by server');
    }

    if (!responseData.user) {
        console.error('No user data returned from register endpoint');
        throw new Error('Authentication error: No user data provided by server');
    }

    const userId = responseData.user.id;
    const username = responseData.user.username;
    const userType = responseData.user.user_type;

    if (userId === undefined || !username || !userType) {
        console.error('Incomplete user data returned from register endpoint', responseData.user);
        throw new Error('Authentication error: Incomplete user data provided by server');
    }

    localStorage.setItem('token', responseData.token);
    localStorage.setItem('userId', userId.toString());
    localStorage.setItem('userType', userType);
    localStorage.setItem('username', username);

    return responseData.user;
}

export async function login(data: LoginData): Promise<User> {
    const response = await fetch(`${API_URL}/api/auth/login/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Login failed');
    }

    const responseData = await response.json() as AuthResponse;

    if (!responseData.token) {
        console.error('No token returned from login endpoint');
        throw new Error('Authentication error: No token provided by server');
    }

    if (!responseData.user) {
        console.error('No user data returned from login endpoint');
        throw new Error('Authentication error: No user data provided by server');
    }

    const userId = responseData.user.id;
    const username = responseData.user.username;
    const userType = responseData.user.user_type;

    if (userId === undefined || !username || !userType) {
        console.error('Incomplete user data returned from login endpoint', responseData.user);
        throw new Error('Authentication error: Incomplete user data provided by server');
    }

    localStorage.setItem('token', responseData.token);
    localStorage.setItem('userId', userId.toString());
    localStorage.setItem('userType', userType);
    localStorage.setItem('username', username);

    return responseData.user;
}

export async function logout(): Promise<void> {
    try {
        await fetch(`${API_URL}/api/auth/logout/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
            },
            credentials: 'include',
        });
    } catch (error) {
        console.error('Error during logout:', error);
    } finally {
        localStorage.removeItem('token');
        localStorage.removeItem('userId');
        localStorage.removeItem('username');
        localStorage.removeItem('userType');
    }
}

export async function getCurrentUser(): Promise<User | null> {
    try {
        const token = localStorage.getItem('token');

        if (!token) {
            return null;
        }

        try {
            const response = await fetchWithDjangoAuth('/api/auth/user/');

            if (!response.user) {
                return null;
            }

            const user = response.user;
            if (!user.id || !user.username || !user.email || !user.user_type) {
                console.error('Incomplete user data returned from getCurrentUser endpoint', user);
                throw new Error('Authentication error: Incomplete user data provided by server');
            }


            return user;
        } catch (error) {
            if (error instanceof Error &&
                (error.message.includes('Authentication required') ||
                    error.message.includes('401'))) {

                localStorage.removeItem('token');
                localStorage.removeItem('userId');
                localStorage.removeItem('username');
                localStorage.removeItem('userType');

            }
            throw error;
        }
    } catch (error) {
        console.error('Error fetching current user:', error);
        localStorage.removeItem('token');
        localStorage.removeItem('userId');
        localStorage.removeItem('username');
        localStorage.removeItem('userType');
        return null;
    }
} 