'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User, login as apiLogin, register as apiRegister, logout as apiLogout, getCurrentUser } from '@/api/auth';
import { useRouter } from 'next/navigation';

interface AuthContextType {
    user: User | null;
    loading: boolean;
    login: (username: string, password: string) => Promise<void>;
    register: (username: string, email: string, password: string, userType: string) => Promise<void>;
    logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        const loadUser = async () => {
            try {
                const currentUser = await getCurrentUser();
                setUser(currentUser);
            } catch (error) {
                console.error('Failed to load user:', error);
                if (error instanceof Error &&
                    (error.message.includes('Authentication required') ||
                        error.message.includes('401'))) {
                    console.log('Auth error detected, redirecting to login');
                    router.push('/auth/login');
                }
            } finally {
                setLoading(false);
            }
        };

        loadUser();
    }, [router]);

    const login = async (username: string, password: string) => {
        try {
            const loggedInUser = await apiLogin({ username, password });
            setUser(loggedInUser);
        } catch (error) {
            throw error;
        }
    };

    const register = async (username: string, email: string, password: string, userType: string) => {
        try {
            const newUser = await apiRegister({ username, email, password, user_type: userType });
            setUser(newUser);
        } catch (error) {
            throw error;
        }
    };

    const logout = async () => {
        try {
            await apiLogout();
            setUser(null);
            router.push('/auth/login');
        } catch (error) {
            console.error('Logout error:', error);
            setUser(null);
            router.push('/auth/login');
        }
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, register, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
} 