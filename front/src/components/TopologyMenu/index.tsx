'use client';

import { useState } from 'react';
import styles from './TopologyMenu.module.css';
import { topologyApi } from '@/api/network';
import { useAuth } from '@/context/AuthContext';
import { useNetwork, Topology } from '@/context/NetworkContext';
import { useRouter } from 'next/navigation';

interface Device {
    id: string;
    type: string;
    x: number;
    y: number;
    name?: string;
}

interface Connection {
    id: string;
    from: string;
    to: string;
}

interface TopologyMenuProps {
    onTopologyChange: (topologyId: number) => void;
    devices: Device[];
    connections: Connection[];
}

export function TopologyMenu({ onTopologyChange, devices, connections }: TopologyMenuProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [newTopologyName, setNewTopologyName] = useState('');
    const [newTopologyDesc, setNewTopologyDesc] = useState('');
    const { user } = useAuth();
    const {
        showTopologyCreateModal,
        setShowTopologyCreateModal,
        topologies,
        fetchTopologies,
        topologiesError,
        loadingTopologies
    } = useNetwork();
    const router = useRouter();

    const handleCreateTopology = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const hosts = devices
                .filter(d => d.type !== 'switch')
                .map(d => ({
                    name: d.id,
                    type: 'host'
                }));

            const switches = devices
                .filter(d => d.type === 'switch')
                .map(d => ({
                    name: d.id,
                    type: 'switch'
                }));

            const links = connections.map(conn => ({
                node1: conn.from,
                node2: conn.to
            }));

            const result = await topologyApi.create({
                name: newTopologyName,
                description: newTopologyDesc,
                hosts,
                switches,
                links
            });

            setShowTopologyCreateModal(false);
            setNewTopologyName('');
            setNewTopologyDesc('');

            await fetchTopologies();

            if (result && result.topology_id) {
                onTopologyChange(result.topology_id);
            } else {
                const updatedTopologies = await topologyApi.list();
                const newTopology = updatedTopologies.find((t: Topology) => t.name === newTopologyName);
                if (newTopology) {
                    onTopologyChange(newTopology.id);
                }
            }
        } catch (error) {
            console.error('Error creating topology:', error);
            if (error instanceof Error && error.message.includes('Authentication required')) {
                router.push('/auth/login');
            }
        }
    };

    const handleActivateTopology = async (id: number) => {
        try {
            await topologyApi.activate(id);
            await fetchTopologies();
            onTopologyChange(id);
            setIsOpen(false);
        } catch (error) {
            console.error('Error activating topology:', error);
            if (error instanceof Error && error.message.includes('Authentication required')) {
                router.push('/auth/login');
            }
        }
    };

    const handleDeleteTopology = async (id: number) => {
        if (!confirm('Вы уверены, что хотите удалить эту топологию?')) return;

        try {
            await topologyApi.delete(id);
            await fetchTopologies();

            onTopologyChange(0);
        } catch (error) {
            console.error('Error deleting topology:', error);
            if (error instanceof Error && error.message.includes('Authentication required')) {
                router.push('/auth/login');
            }
        }
    };

    if (!user) {
        return (
            <div className={styles.dropdown}>
                <button className={styles.button} onClick={() => router.push('/auth/login')}>
                    Войти в систему
                </button>
            </div>
        );
    }

    return (
        <>
            <div className={styles.dropdown}>
                <button className={styles.button} onClick={() => setIsOpen(!isOpen)}>
                    Топология
                    <span>{isOpen ? '▼' : '▲'}</span>
                </button>

                {isOpen && (
                    <div className={styles.menu}>
                        {topologiesError && <div className={styles.error}>{topologiesError}</div>}
                        <div className={styles.menuItem} onClick={() => setShowTopologyCreateModal(true)}>
                            + Добавить
                        </div>
                        <div className={styles.separator} />
                        <div className={styles.topologyList}>
                            {loadingTopologies ? (
                                <div className={styles.menuItem}>Загрузка...</div>
                            ) : topologies.length === 0 ? (
                                <div className={styles.menuItem}>Топологии не найдены</div>
                            ) : (
                                topologies.map(topology => (
                                    <div key={topology.id} className={styles.topologyItem}>
                                        <div
                                            className={`${styles.topologyName} ${topology.is_active ? styles.activeTopology : ''}`}
                                            onClick={() => handleActivateTopology(topology.id)}
                                            title={topology.description || topology.name}
                                        >
                                            {topology.name}
                                        </div>
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleDeleteTopology(topology.id);
                                            }}
                                            className={styles.deleteButton}
                                            title="Удалить топологию"
                                        >
                                            ×
                                        </button>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                )}
            </div>

            {showTopologyCreateModal && (
                <div className={styles.overlay} onClick={() => setShowTopologyCreateModal(false)}>
                    <div className={styles.modal} onClick={e => e.stopPropagation()}>
                        <form onSubmit={handleCreateTopology} className={styles.form}>
                            <div className={styles.formGroup}>
                                <label>Название</label>
                                <input
                                    type="text"
                                    className={styles.input}
                                    value={newTopologyName}
                                    onChange={e => setNewTopologyName(e.target.value)}
                                    required
                                />
                            </div>
                            <div className={styles.formGroup}>
                                <label>Описание</label>
                                <textarea
                                    className={styles.input}
                                    value={newTopologyDesc}
                                    onChange={e => setNewTopologyDesc(e.target.value)}
                                />
                            </div>
                            <div className={styles.buttonGroup}>
                                <button
                                    type="button"
                                    className={styles.cancelButton}
                                    onClick={() => setShowTopologyCreateModal(false)}
                                >
                                    Отмена
                                </button>
                                <button type="submit" className={styles.submitButton}>
                                    Создать
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </>
    );
} 