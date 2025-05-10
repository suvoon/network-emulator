'use client';

import React from 'react';
import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '../../context/AuthContext';
import { useNetwork } from '../../context/NetworkContext';
import { TopologyMenu } from '../TopologyMenu';
import styles from './navbar.module.css';

interface NavbarProps {
    isDashboardPage?: boolean;
}

export function Navbar({ isDashboardPage = false }: NavbarProps) {
    const { user, logout, loading } = useAuth();
    const pathname = usePathname();
    const isTutorialPage = pathname === '/tutorial';

    const network = !isTutorialPage ? useNetwork() : null;
    const hasTopologies = network?.hasTopologies ?? false;

    const router = useRouter();

    const handleLogout = async () => {
        await logout();
        router.push('/auth/login');
    };

    const handleTopologyChange = (topologyId: number) => {
        if (network) {
            network.setCurrentTopologyId(topologyId);
        }
    };

    const handleTracePacket = () => {
        if (network) {
            network.setShowPacketTracer(true);
        }
    };

    const isTeacher = user && user.user_type === 'EDUCATOR';

    return (
        <nav className={styles.navbar}>
            <div className={styles.logo}>
                <Link href="/">{user?.username}</Link>
            </div>
            <div className={styles.links}>
                <div className={styles.actions}>
                    {!isTutorialPage && !isDashboardPage && (
                        <>
                            <TopologyMenu
                                onTopologyChange={handleTopologyChange}
                                devices={network?.devices || []}
                                connections={network?.connections || []}
                            />
                            <button
                                className={`${styles.actionButton} ${!hasTopologies ? styles.disabledButton : ''}`}
                                onClick={handleTracePacket}
                                disabled={!hasTopologies}
                                title={!hasTopologies ? "Создайте топологию для использования трассировки" : ""}
                            >
                                Трассировка пакета
                            </button>
                        </>
                    )}
                    {isTutorialPage || isDashboardPage ? (
                        <Link
                            href="/"
                            className={styles.actionButton}
                        >
                            Эмулятор
                        </Link>
                    ) : (
                        <Link
                            href="/tutorial"
                            className={`${styles.actionButton} ${isTutorialPage ? styles.activeLink : ''}`}
                        >
                            {isTeacher ? 'Учебные материалы' : 'Обучение'}
                        </Link>
                    )}

                    {isTeacher && !isDashboardPage && (
                        <Link
                            href="/educator/dashboard"
                            className={`${styles.actionButton} ${pathname?.startsWith('/educator') ? styles.activeLink : ''}`}
                        >
                            Панель преподавателя
                        </Link>
                    )}
                </div>
                {!loading && (
                    user ? (
                        <>
                            <button
                                onClick={handleLogout}
                                className={styles.logoutButton}
                            >
                                Выйти
                            </button>
                        </>
                    ) : (
                        <>
                            <Link href="/auth/login" className={styles.navLink}>
                                Вход
                            </Link>
                            <Link href="/auth/register" className={styles.navLink}>
                                Регистрация
                            </Link>
                        </>
                    )
                )}
            </div>
        </nav>
    );
}