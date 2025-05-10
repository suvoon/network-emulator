"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { authApi } from '@/api/network';

export default function LoginPage() {
    const router = useRouter();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            const response = await authApi.login(username, password);

            localStorage.setItem('token', response.token);

            if (response.user) {
                localStorage.setItem('userId', response.user.id.toString());

                if (response.user.user_type) {
                    localStorage.setItem('userType', response.user.user_type);
                    const isEducator = response.user.user_type === 'EDUCATOR';
                    localStorage.setItem('isStaff', isEducator.toString());
                } else {
                    localStorage.setItem('userType', 'STUDENT');
                    localStorage.setItem('isStaff', 'false');
                }

                localStorage.setItem('username', response.user.username);
            }

            router.push('/');
        } catch (err) {
            console.error(err);
            setError('Неверный логин или пароль');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex min-h-screen items-center justify-center p-4">
            <div className="w-full max-w-md">
                <h1 className="text-2xl font-bold text-center mb-6">Войти в систему</h1>

                {error && (
                    <div className="mb-4 p-3 text-red-700 bg-red-100 rounded">
                        {error}
                    </div>
                )}

                <form onSubmit={handleLogin} className="bg-white shadow-md rounded px-8 pt-6 pb-8 mb-4">
                    <div className="mb-4">
                        <label htmlFor="username" className="block text-gray-700 text-sm font-bold mb-2">
                            Имя пользователя
                        </label>
                        <input
                            type="text"
                            id="username"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                            required
                        />
                    </div>

                    <div className="mb-6">
                        <label htmlFor="password" className="block text-gray-700 text-sm font-bold mb-2">
                            Пароль
                        </label>
                        <input
                            type="password"
                            id="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                            required
                        />
                    </div>

                    <div className="flex items-center justify-between">
                        <button
                            type="submit"
                            disabled={loading}
                            className={`bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline ${loading ? 'opacity-50 cursor-not-allowed' : ''
                                }`}
                        >
                            {loading ? 'Вход...' : 'Войти'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
} 