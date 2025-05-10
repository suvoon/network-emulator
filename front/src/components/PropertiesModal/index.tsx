'use client';

import { useState, useEffect } from 'react';
import styles from './PropertiesModal.module.css';
import { DeviceType } from '@/components/DeviceIcon/types';
import { Device } from '@/context/NetworkContext';
import { nodeApi } from '@/api/network';

interface PropertiesModalProps {
    device: {
        id: string;
        type: DeviceType;
        name?: string;
        display_name?: string;
        ip_address?: string;
    };
    onClose: () => void;
    onSave: (updatedDevice: {
        id: string;
        display_name?: string;
        ip_address?: string;
    }) => Promise<void>;
}

interface Interface {
    name: string;
    ip: string;
    subnet_mask?: number;
}

type RouterTab = 'general' | 'interfaces';

export function PropertiesModal({ device, onClose, onSave }: PropertiesModalProps) {
    const [displayName, setDisplayName] = useState(device.display_name || device.name || '');
    const [ipAddress, setIpAddress] = useState(device.ip_address || '');
    const [error, setError] = useState('');
    const [isSaving, setIsSaving] = useState(false);
    const [activeTab, setActiveTab] = useState<RouterTab>('general');

    const [interfaces, setInterfaces] = useState<Interface[]>([]);
    const [newInterfaceName, setNewInterfaceName] = useState('');
    const [newInterfaceIp, setNewInterfaceIp] = useState('');
    const [newInterfaceSubnetMask, setNewInterfaceSubnetMask] = useState('24');
    const [interfacesLoading, setInterfacesLoading] = useState(true);

    const [success, setSuccess] = useState('');

    useEffect(() => {
        if (device.type === 'router' && activeTab === 'interfaces') {
            console.log('Fetching router interfaces for:', device.id);
            fetchRouterInterfaces();
        }
    }, [device.type, activeTab, device.id]);

    const fetchRouterInterfaces = async () => {
        try {
            console.log('Starting interface fetch for router:', device.id);
            setInterfacesLoading(true);

            const response = await nodeApi.getRouterInterfaces(device.id);
            console.log('Router interfaces response:', response);

            if (response.interfaces) {
                console.log('Setting interfaces:', response.interfaces);
                setInterfaces(response.interfaces);
            } else {
                console.warn('No interfaces found or API not implemented');
                setInterfaces([]);
            }

            setInterfacesLoading(false);
        } catch (err) {
            console.error('Error loading router interfaces:', err);
            setError('Ошибка загрузки интерфейсов маршрутизатора');
            setInterfacesLoading(false);
            setInterfaces([]);
        }
    };

    const handleSave = async () => {
        try {
            setError('');
            setIsSaving(true);

            let processedIpAddress = ipAddress;
            if (device.type !== 'switch' && processedIpAddress && !processedIpAddress.includes('/')) {
                processedIpAddress = `${processedIpAddress}/24`;
            }

            if (device.type !== 'switch' && processedIpAddress && !isValidIpAddress(processedIpAddress)) {
                setError('Недопустимый IP-адрес. Используйте формат xxx.xxx.xxx.xxx или xxx.xxx.xxx.xxx/xx');
                setIsSaving(false);
                return;
            }

            const updatedDevice: {
                id: string;
                display_name?: string;
                ip_address?: string;
            } = {
                id: device.id,
                display_name: displayName,
            };

            if (device.type !== 'switch') {
                updatedDevice.ip_address = processedIpAddress;
            }

            await onSave(updatedDevice);

            onClose();
        } catch (err) {
            setError('Ошибка при сохранении: ' + (err instanceof Error ? err.message : 'Неизвестная ошибка'));
            setIsSaving(false);
        }
    };

    const isValidIpAddress = (ip: string) => {
        const ipRegex = /^(\d{1,3}\.){3}\d{1,3}(\/\d{1,2})?$/;
        if (!ipRegex.test(ip)) return false;

        const octets = ip.split('/')[0].split('.');
        for (const octet of octets) {
            const num = parseInt(octet, 10);
            if (num < 0 || num > 255) return false;
        }

        if (ip.includes('/')) {
            const cidr = parseInt(ip.split('/')[1], 10);
            if (cidr < 0 || cidr > 32) return false;
        }

        return true;
    };

    const getDeviceType = (device: Device) => {
        if (device.type === 'host') return 'Хост';
        if (device.type === 'switch') return 'Коммутатор';
        if (device.type === 'router') return 'Роутер';
        return 'Неизвестно';
    };

    const handleAddInterface = async () => {
        if (!newInterfaceName || !newInterfaceIp) {
            setError('Введите имя интерфейса и IP-адрес');
            return;
        }

        let processedIp = newInterfaceIp;
        if (!processedIp.includes('/')) {
            processedIp = `${processedIp}/${newInterfaceSubnetMask}`;
        }

        if (!isValidIpAddress(processedIp)) {
            setError('Недопустимый IP-адрес. Используйте формат xxx.xxx.xxx.xxx/xx');
            return;
        }

        try {
            setError('');
            const data = {
                router_name: device.id,
                interface_name: newInterfaceName,
                ip_address: processedIp,
                subnet_mask: parseInt(newInterfaceSubnetMask, 10)
            };

            const response = await nodeApi.configureRouterInterface(data);

            if (response.success) {
                setNewInterfaceName('');
                setNewInterfaceIp('');
                setNewInterfaceSubnetMask('24');

                setSuccess('Интерфейс успешно добавлен');
                setTimeout(() => setSuccess(''), 3000);

                fetchRouterInterfaces();
            } else {
                setError('Ошибка при добавлении интерфейса');
            }
        } catch (err) {
            setError('Ошибка при добавлении интерфейса: ' + (err instanceof Error ? err.message : 'Неизвестная ошибка'));
        }
    };

    return (
        <div className={styles.overlay} onClick={onClose}>
            <div className={styles.modal} onClick={e => e.stopPropagation()}>
                <div className={styles.header}>
                    <h2 className={styles.title}>Свойства устройства</h2>
                    <button className={styles.closeButton} onClick={onClose}>×</button>
                </div>

                {device.type === 'router' && (
                    <div className={styles.tabs}>
                        <button
                            className={`${styles.tab} ${activeTab === 'general' ? styles.activeTab : ''}`}
                            onClick={() => setActiveTab('general')}
                        >
                            Общие
                        </button>
                        <button
                            className={`${styles.tab} ${activeTab === 'interfaces' ? styles.activeTab : ''}`}
                            onClick={() => setActiveTab('interfaces')}
                        >
                            Интерфейсы
                        </button>
                    </div>
                )}

                <div className={styles.content}>
                    {(activeTab === 'general' || device.type !== 'router') && (
                        <>
                            <div className={styles.formGroup}>
                                <label className={styles.label}>Тип устройства</label>
                                <div className={styles.value}>
                                    {getDeviceType(device as Device)}
                                </div>
                            </div>

                            <div className={styles.formGroup}>
                                <label className={styles.label}>Системное имя</label>
                                <div className={styles.value}>{device.id}</div>
                            </div>

                            <div className={styles.formGroup}>
                                <label className={styles.label}>Отображаемое имя</label>
                                <input
                                    type="text"
                                    className={styles.input}
                                    value={displayName}
                                    onChange={(e) => setDisplayName(e.target.value)}
                                    placeholder="Введите отображаемое имя"
                                />
                            </div>

                            {device.type !== 'switch' && (
                                <div className={styles.formGroup}>
                                    <label className={styles.label}>
                                        {device.type === 'router' ? 'Основной IP-адрес' : 'IP-адрес'}
                                    </label>
                                    <input
                                        type="text"
                                        className={styles.input}
                                        value={ipAddress}
                                        onChange={(e) => setIpAddress(e.target.value)}
                                        placeholder="Например: 10.0.0.1 (маска /24 будет добавлена автоматически)"
                                    />
                                    <div className={styles.hint}>
                                        {device.type === 'host'
                                            ? 'IP-адрес хоста (можно без маски, /24 будет добавлена автоматически)'
                                            : 'IP-адрес маршрутизатора (можно без маски, /24 будет добавлена автоматически)'}
                                    </div>
                                </div>
                            )}
                        </>
                    )}

                    {device.type === 'router' && activeTab === 'interfaces' && (
                        <div>
                            {interfacesLoading ? (
                                <div className={styles.loading}>Загрузка интерфейсов...</div>
                            ) : (
                                <>
                                    <div className={styles.section}>
                                        <h3 className={styles.sectionTitle}>Интерфейсы</h3>

                                        {interfaces.length > 0 ? (
                                            <div className={styles.tableContainer}>
                                                <table className={styles.table}>
                                                    <thead>
                                                        <tr>
                                                            <th>Интерфейс</th>
                                                            <th>IP-адрес</th>
                                                            <th>Маска</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {interfaces.map((intf, index) => (
                                                            <tr key={index}>
                                                                <td>{intf.name}</td>
                                                                <td>{intf.ip ? intf.ip.split('/')[0] : '-'}</td>
                                                                <td>{intf.ip && intf.ip.includes('/') ? intf.ip.split('/')[1] : (intf.subnet_mask || '-')}</td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        ) : (
                                            <div className={styles.emptyState}>
                                                Нет настроенных интерфейсов
                                            </div>
                                        )}

                                        <div className={styles.formGroup}>
                                            <h4>Добавить интерфейс</h4>

                                            <div className={styles.formRow}>
                                                <div className={styles.formField}>
                                                    <label>Имя интерфейса</label>
                                                    <input
                                                        type="text"
                                                        value={newInterfaceName}
                                                        onChange={(e) => setNewInterfaceName(e.target.value)}
                                                        placeholder="например: eth0"
                                                    />
                                                </div>

                                                <div className={styles.formField}>
                                                    <label>IP-адрес</label>
                                                    <input
                                                        type="text"
                                                        value={newInterfaceIp}
                                                        onChange={(e) => setNewInterfaceIp(e.target.value)}
                                                        placeholder="например: 192.168.1.1"
                                                    />
                                                </div>

                                                <div className={styles.formField}>
                                                    <label>Маска подсети</label>
                                                    <select
                                                        value={newInterfaceSubnetMask}
                                                        onChange={(e) => setNewInterfaceSubnetMask(e.target.value)}
                                                    >
                                                        <option value="8">8 (255.0.0.0)</option>
                                                        <option value="16">16 (255.255.0.0)</option>
                                                        <option value="24">24 (255.255.255.0)</option>
                                                        <option value="30">30 (255.255.255.252)</option>
                                                        <option value="32">32 (255.255.255.255)</option>
                                                    </select>
                                                </div>

                                                <button
                                                    className={styles.addButton}
                                                    onClick={handleAddInterface}
                                                >
                                                    Добавить
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </>
                            )}
                        </div>
                    )}

                    {error && <div className={styles.error}>{error}</div>}
                    {success && <div className={styles.success}>{success}</div>}

                    <div className={styles.actions}>
                        <button
                            className={styles.cancelButton}
                            onClick={onClose}
                            disabled={isSaving}
                        >
                            Отмена
                        </button>
                        <button
                            className={styles.saveButton}
                            onClick={handleSave}
                            disabled={isSaving}
                        >
                            {isSaving ? 'Сохранение...' : 'Сохранить'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
} 