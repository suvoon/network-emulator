'use client';

import { useState, useEffect } from 'react';
import Cookies from 'js-cookie';
import styles from './Canvas.module.css';
import { ContextMenu, Connector, DeviceIcon } from '../';
import { DeviceType } from '../DeviceIcon/types';
import { icons } from '../DeviceIcon';
import { PacketTracer } from '../PacketTracer';
import { Notification } from '../Notification';
import { useNetwork, Device, Connection } from '../../context/NetworkContext';
import { PropertiesModal } from '../PropertiesModal';
import { topologyApi, nodeApi, linkApi } from '@/api/network';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';

interface ContextMenuState {
    show: boolean;
    x: number;
    y: number;
    deviceId: string | null;
}

interface NotificationState {
    show: boolean;
    message: string;
    type: 'success' | 'error';
}

interface ValidationResult {
    valid: boolean;
    errors: string[];
    warnings: string[];
}

export function Canvas() {
    const {
        devices,
        setDevices: setNetworkDevices,
        connections,
        setConnections: setNetworkConnections,
        showPacketTracer,
        setShowPacketTracer,
        currentTopologyId,
        setCurrentTopologyId,
        setShowTopologyCreateModal,
        topologies
    } = useNetwork();

    const { user } = useAuth();
    const router = useRouter();

    const [draggedDevice, setDraggedDevice] = useState<string | null>(null);
    const [selectedDevice, setSelectedDevice] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [contextMenu, setContextMenu] = useState<ContextMenuState>({
        show: false,
        x: 0,
        y: 0,
        deviceId: null,
    });
    const [notification, setNotification] = useState<NotificationState>({
        show: false,
        message: '',
        type: 'success'
    });
    const [showProperties, setShowProperties] = useState<boolean>(false);
    const [selectedDeviceForProperties, setSelectedDeviceForProperties] = useState<Device | null>(null);
    const [hasTopologies, setHasTopologies] = useState<boolean | null>(null);
    const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
    const [showValidationResults, setShowValidationResults] = useState<boolean>(false);

    useEffect(() => {
        const loadActiveTopology = async () => {
            if (!user) {
                return;
            }

            setIsLoading(true);
            try {

                if (topologies.length === 0) {
                    setHasTopologies(false);
                    setIsLoading(false);
                    return;
                }

                setHasTopologies(true);
                const activeTopology = topologies.find(t => t.is_active);

                if (activeTopology) {
                    Cookies.set('activeTopologyId', activeTopology.id.toString());
                    setCurrentTopologyId(activeTopology.id);

                    const topology = await topologyApi.get(activeTopology.id);

                    const newDevices: Device[] = [
                        ...(topology.hosts || []).map((host: any) => ({
                            id: host.name,
                            type: 'host' as DeviceType,
                            x: host.x || 100,
                            y: host.y || 100,
                            name: host.name,
                            display_name: host.display_name || host.name,
                            ip_address: host.ip
                        })),
                        ...(topology.switches || []).map((switch_: any) => ({
                            id: switch_.name,
                            type: 'switch' as DeviceType,
                            x: switch_.x || 200,
                            y: switch_.y || 200,
                            name: switch_.name,
                            display_name: switch_.display_name || switch_.name,
                            ip_address: switch_.ip
                        })),
                        ...(topology.routers || []).map((router_: any) => ({
                            id: router_.name,
                            type: 'router' as DeviceType,
                            x: router_.x || 300,
                            y: router_.y || 300,
                            name: router_.name,
                            display_name: router_.display_name || router_.name,
                            ip_address: router_.ip
                        }))
                    ];

                    const newConnections: Connection[] = (topology.links || []).map((link: any, index: number) => ({
                        id: `conn-${index}`,
                        from: link.node1,
                        to: link.node2
                    }));

                    setNetworkDevices(newDevices);
                    setNetworkConnections(newConnections);

                    await topologyApi.activate(activeTopology.id);
                }
            } catch (error) {
                console.error('Error in loadActiveTopology:', error);
                if (error instanceof Error && error.message.includes('Authentication required')) {
                    router.push('/auth/login');
                } else {
                    setNotification({
                        show: true,
                        message: error instanceof Error ? error.message : 'Failed to load topology',
                        type: 'error'
                    });
                }
            } finally {
                setIsLoading(false);
            }
        };

        const loadTopology = async () => {
            if (!user) {
                return;
            }

            setIsLoading(true);
            try {
                if (topologies.length === 0) {
                    setHasTopologies(false);
                    setIsLoading(false);
                    Cookies.remove('activeTopologyId');
                    return;
                }

                setHasTopologies(true);

                const savedTopologyId = currentTopologyId || Cookies.get('activeTopologyId');

                if (savedTopologyId) {
                    try {
                        const topology = await topologyApi.get(Number(savedTopologyId));

                        const newDevices: Device[] = [
                            ...(topology.hosts || []).map((host: any) => ({
                                id: host.name,
                                type: 'host' as DeviceType,
                                x: host.x || 100,
                                y: host.y || 100,
                                name: host.name,
                                display_name: host.display_name || host.name,
                                ip_address: host.ip
                            })),
                            ...(topology.switches || []).map((switch_: any) => ({
                                id: switch_.name,
                                type: 'switch' as DeviceType,
                                x: switch_.x || 200,
                                y: switch_.y || 200,
                                name: switch_.name,
                                display_name: switch_.display_name || switch_.name,
                                ip_address: switch_.ip
                            })),
                            ...(topology.routers || []).map((router_: any) => ({
                                id: router_.name,
                                type: 'router' as DeviceType,
                                x: router_.x || 300,
                                y: router_.y || 300,
                                name: router_.name,
                                display_name: router_.display_name || router_.name,
                                ip_address: router_.ip
                            }))
                        ];

                        const newConnections: Connection[] = (topology.links || []).map((link: any, index: number) => ({
                            id: `conn-${index}`,
                            from: link.node1,
                            to: link.node2
                        }));

                        setNetworkDevices(newDevices);
                        setNetworkConnections(newConnections);

                        await topologyApi.activate(Number(savedTopologyId));
                    } catch (error) {
                        console.log(error);
                        console.error('Failed to load saved topology, falling back to active topology');
                        Cookies.remove('activeTopologyId');
                        await loadActiveTopology();
                    }
                } else {
                    await loadActiveTopology();
                }
            } catch (error) {
                console.error('Error in loadTopology:', error);
                if (error instanceof Error && error.message.includes('Authentication required')) {
                    router.push('/auth/login');
                } else {
                    setNotification({
                        show: true,
                        message: error instanceof Error ? error.message : 'Failed to load topology',
                        type: 'error'
                    });
                }
            } finally {
                setIsLoading(false);
            }
        };

        loadTopology();
    }, [setNetworkDevices, setNetworkConnections, currentTopologyId, setCurrentTopologyId, user, router, topologies]);

    const generateDeviceName = (type: string) => {
        const prefix = type === 'switch' ? 's' : type === 'router' ? 'r' : 'h';
        const timestamp = Date.now();
        const randomNum = Math.floor(Math.random() * 1000);
        return `${prefix}${timestamp % 100}${randomNum % 100}`;
    };

    const handleDrop = async (e: React.DragEvent) => {
        e.preventDefault();
        const deviceType = e.dataTransfer.getData('deviceType') as DeviceType;

        if (!draggedDevice) {
            const rect = e.currentTarget.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const deviceId = generateDeviceName(deviceType);
            const newDevice = {
                id: deviceId,
                type: deviceType,
                x,
                y,
                name: deviceId,
                display_name: deviceId
            };

            try {
                let apiMethod;
                if (deviceType === 'switch') {
                    apiMethod = nodeApi.addSwitch;
                } else if (deviceType === 'router') {
                    apiMethod = nodeApi.addRouter;
                } else {
                    apiMethod = nodeApi.addHost;
                }

                const data = await apiMethod({
                    name: deviceId,
                    display_name: deviceId,
                    x: x,
                    y: y,
                    ...(deviceType !== 'switch' && deviceType !== 'router' && { ip: null })
                });

                if (!data.success) {
                    throw new Error(data.error || 'Failed to create device');
                }

                setNetworkDevices((prev: Device[]) => [...prev, newDevice]);
                setNotification({
                    show: true,
                    message: `${deviceType} создан успешно`,
                    type: 'success'
                });
            } catch (error) {
                console.error('Error creating device:', error);
                setNotification({
                    show: true,
                    message: error instanceof Error ? error.message : 'Failed to create device',
                    type: 'error'
                });
            }
        }
    };

    const handleDeviceDragStart = (e: React.DragEvent, device: Device) => {
        setDraggedDevice(device.id);
        e.dataTransfer.setData('text/plain', '');
    };

    const handleDeviceDrag = (e: React.DragEvent) => {
        if (draggedDevice) {
            e.preventDefault();
            const rect = e.currentTarget.getBoundingClientRect();

            let x = e.clientX - rect.left;
            let y = e.clientY - rect.top;

            x = Math.max(32, Math.min(x, rect.width - 32));
            y = Math.max(32, Math.min(y, rect.height - 32));

            setNetworkDevices((prev) => prev.map((device) =>
                device.id === draggedDevice
                    ? { ...device, x, y }
                    : device
            ));
        }
    };

    const handleDeviceDragEnd = async () => {
        if (draggedDevice) {
            const deviceId = draggedDevice;
            const device = devices.find(d => d.id === deviceId);

            if (device) {
                console.log('Current device position:', { x: device.x, y: device.y });

                try {
                    console.log('Sending position update to backend:', {
                        name: deviceId,
                        x: device.x,
                        y: device.y
                    });

                    const response = await nodeApi.updatePosition({
                        name: deviceId,
                        x: device.x,
                        y: device.y
                    });

                    console.log('Backend response:', response);
                } catch (error) {
                    console.error('Error updating device position:', error);
                    if (error instanceof Error && error.message.includes('Authentication required')) {
                        router.push('/auth/login');
                    } else {
                        setNotification({
                            show: true,
                            message: 'Failed to update device position',
                            type: 'error'
                        });
                    }
                }
            }
            setDraggedDevice(null);
        }
    };

    const handleContextMenu = (e: React.MouseEvent, deviceId: string) => {
        e.preventDefault();
        setContextMenu({
            show: true,
            x: e.clientX,
            y: e.clientY,
            deviceId,
        });
    };

    const handleDeleteDevice = async () => {
        if (contextMenu.deviceId) {
            try {
                const device = devices.find(d => d.id === contextMenu.deviceId);
                if (!device) return;

                if (device.type === 'switch') {
                    await nodeApi.deleteSwitch(contextMenu.deviceId);
                } else if (device.type === 'router') {
                    await nodeApi.deleteRouter(contextMenu.deviceId);
                } else {
                    await nodeApi.deleteHost(contextMenu.deviceId);
                }

                setNetworkDevices(devices.filter(device => device.id !== contextMenu.deviceId));
                setContextMenu({ show: false, x: 0, y: 0, deviceId: null });
                setNotification({
                    show: true,
                    message: 'Device deleted successfully',
                    type: 'success'
                });
            } catch (error) {
                console.error('Error deleting device:', error);
                setNotification({
                    show: true,
                    message: error instanceof Error ? error.message : 'Failed to delete device',
                    type: 'error'
                });
            }
        }
    };

    const handleDeviceClick = async (e: React.MouseEvent, deviceId: string) => {
        e.stopPropagation();

        if (contextMenu.show) {
            setContextMenu({ ...contextMenu, show: false });
            return;
        }

        if (selectedDevice && selectedDevice !== deviceId) {
            try {
                await linkApi.add({
                    node1: selectedDevice,
                    node2: deviceId
                });

                const newConnection: Connection = {
                    id: `conn-${Date.now()}`,
                    from: selectedDevice,
                    to: deviceId
                };
                setNetworkConnections([...connections, newConnection]);
                setSelectedDevice(null);

                setNotification({
                    show: true,
                    message: 'Connection added successfully',
                    type: 'success'
                });
            } catch (error) {
                console.error('Error creating connection:', error);
                if (error instanceof Error && error.message.includes('Authentication required')) {
                    router.push('/auth/login');
                } else {
                    setNotification({
                        show: true,
                        message: error instanceof Error ? error.message : 'Failed to create connection',
                        type: 'error'
                    });
                }
                setSelectedDevice(null);
            }
        } else {
            setSelectedDevice(deviceId);
        }
    };

    const handleCanvasClick = () => {
        setSelectedDevice(null);
        setContextMenu({ show: false, x: 0, y: 0, deviceId: null });
    };

    const handleDeleteConnection = async (connectionId: string) => {
        const connection = connections.find(c => c.id === connectionId);
        if (!connection) return;

        try {
            await linkApi.delete({
                node1: connection.from,
                node2: connection.to
            });

            setNetworkConnections(connections.filter(c => c.id !== connectionId));

            setNotification({
                show: true,
                message: 'Connection deleted successfully',
                type: 'success'
            });
        } catch (error) {
            console.error('Error deleting connection:', error);
            if (error instanceof Error && error.message.includes('Authentication required')) {
                router.push('/auth/login');
            } else {
                setNotification({
                    show: true,
                    message: error instanceof Error ? error.message : 'Failed to delete connection',
                    type: 'error'
                });
            }
        }
    };

    const clearNotification = () => {
        setNotification(prev => ({ ...prev, show: false }));
    };

    const handleClosePacketTracer = () => {
        setShowPacketTracer(false);
    };

    const handlePropertiesClick = () => {
        if (contextMenu.deviceId) {
            const device = devices.find(d => d.id === contextMenu.deviceId);
            if (device) {
                setSelectedDeviceForProperties(device);
                setShowProperties(true);
            }
            setContextMenu({ show: false, x: 0, y: 0, deviceId: null });
        }
    };

    const handleUpdateDeviceProperties = async (updatedDevice: {
        id: string;
        display_name?: string;
        ip_address?: string;
    }) => {
        try {
            const device = devices.find(d => d.id === updatedDevice.id);
            if (!device) return;

            if (updatedDevice.display_name && updatedDevice.display_name !== device.display_name) {
                await nodeApi.updateDisplayName({
                    name: updatedDevice.id,
                    display_name: updatedDevice.display_name
                });
            }

            if (updatedDevice.ip_address && updatedDevice.ip_address !== device.ip_address) {
                let endpoint;
                if (device.type === 'switch') {
                    endpoint = nodeApi.updateSwitchIp;
                } else if (device.type === 'router') {
                    endpoint = nodeApi.updateRouterIp;
                } else {
                    endpoint = nodeApi.updateHostIp;
                }

                await endpoint({
                    name: updatedDevice.id,
                    ip: updatedDevice.ip_address
                });
            }

            setNetworkDevices(devices.map(d => {
                if (d.id === updatedDevice.id) {
                    return {
                        ...d,
                        display_name: updatedDevice.display_name || d.display_name,
                        ip_address: updatedDevice.ip_address || d.ip_address
                    };
                }
                return d;
            }));

            setShowProperties(false);
            setNotification({
                show: true,
                message: 'Device updated successfully',
                type: 'success'
            });
        } catch (error) {
            console.error('Error updating device:', error);
            if (error instanceof Error && error.message.includes('Authentication required')) {
                router.push('/auth/login');
            } else {
                setNotification({
                    show: true,
                    message: error instanceof Error ? error.message : 'Failed to update device',
                    type: 'error'
                });
            }
        }
    };

    const handleValidateTopology = async () => {
        try {
            setIsLoading(true);
            const result = await topologyApi.validate();
            setValidationResult(result);
            setShowValidationResults(true);

            if (result.valid) {
                setNotification({
                    show: true,
                    message: 'Топология действительна. Ошибок не обнаружено.',
                    type: 'success'
                });
            } else {
                setNotification({
                    show: true,
                    message: `Топология содержит ${result.errors.length} ошибку(и) и ${result.warnings.length} предупреждение(я).`,
                    type: 'error'
                });
            }
        } catch (error) {
            console.error('Error validating topology:', error);
            setNotification({
                show: true,
                message: error instanceof Error ? error.message : 'Не удалось проверить топологию',
                type: 'error'
            });
        } finally {
            setIsLoading(false);
        }
    };

    const NoTopologiesView = () => {
        const handleCreateTopologyClick = () => {
            setShowTopologyCreateModal(true);
        };

        return (
            <div className={styles.emptyStateContainer}>
                <div className={styles.emptyState}>
                    <h2>Нет активных топологий</h2>
                    <p>Создайте новую топологию, чтобы начать работу</p>
                    <button
                        className={styles.createTopologyButton}
                        onClick={handleCreateTopologyClick}
                    >
                        Создать топологию
                    </button>
                </div>
            </div>
        );
    };

    const ValidationResultsModal = () => {
        if (!validationResult) return null;

        return (
            <div className={styles.validationModal}>
                <div className={styles.validationModalContent}>
                    <h2>
                        Результаты проверки топологии
                        <span
                            className={validationResult.valid ? styles.validBadge : styles.invalidBadge}
                        >
                            {validationResult.valid ? 'Успешно' : 'Ошибка'}
                        </span>
                    </h2>

                    {validationResult.errors.length > 0 && (
                        <>
                            <h3>Ошибки</h3>
                            <ul className={styles.errorList}>
                                {validationResult.errors.map((error, index) => (
                                    <li key={index}>{error}</li>
                                ))}
                            </ul>
                        </>
                    )}

                    {validationResult.warnings.length > 0 && (
                        <>
                            <h3>Предупреждения</h3>
                            <ul className={styles.warningList}>
                                {validationResult.warnings.map((warning, index) => (
                                    <li key={index}>{warning}</li>
                                ))}
                            </ul>
                        </>
                    )}

                    {validationResult.valid && (
                        <p className={styles.successMessage}>
                            Топология соответствует всем принципам сетевого взаимодействия
                        </p>
                    )}

                    <div className={styles.modalButtonsContainer}>
                        <button
                            className={styles.closeButton}
                            onClick={() => setShowValidationResults(false)}
                        >
                            Закрыть
                        </button>
                    </div>
                </div>
            </div>
        );
    };

    return (
        <>
            {hasTopologies === false ? (
                <NoTopologiesView />
            ) : (
                <div
                    className={`${styles.canvas} ${isLoading ? styles.loading : ''}`}
                    onDrop={handleDrop}
                    onDragOver={(e) => {
                        e.preventDefault();
                        handleDeviceDrag(e);
                    }}
                    onClick={handleCanvasClick}
                >
                    {isLoading && (
                        <>
                            <div className={styles.loaderContainer} />
                            <div className={styles.spinnerContainer}>
                                <div className={styles.spinner}></div>
                                <div className={styles.loadingText}>Активация топологии...</div>
                            </div>
                        </>
                    )}

                    <button
                        className={styles.validateButton}
                        onClick={handleValidateTopology}
                        title="Проверить корректность топологии"
                    >
                        Проверить топологию
                    </button>

                    {connections.map((connection) => {
                        const fromDevice = devices.find(d => d.id === connection.from);
                        const toDevice = devices.find(d => d.id === connection.to);

                        if (!fromDevice || !toDevice) return null;

                        return (
                            <Connector
                                key={connection.id}
                                startX={fromDevice.x}
                                startY={fromDevice.y}
                                endX={toDevice.x}
                                endY={toDevice.y}
                                onClick={() => handleDeleteConnection(connection.id)}
                            />
                        );
                    })}

                    {devices.map((device) => (
                        <div
                            key={device.id}
                            className={`${styles.device} ${selectedDevice === device.id ? styles.selected : ''}`}
                            style={{
                                left: device.x,
                                top: device.y,
                            }}
                            draggable
                            onDragStart={(e) => handleDeviceDragStart(e, device)}
                            onDragEnd={() => handleDeviceDragEnd}
                            onContextMenu={(e) => handleContextMenu(e, device.id)}
                            onClick={(e) => handleDeviceClick(e, device.id)}
                        >
                            <DeviceIcon
                                type={device.type as keyof typeof icons}
                                displayName={device.display_name || device.name || device.type}
                                isSelected={selectedDevice === device.id}
                            />
                        </div>
                    ))}
                    {contextMenu.show && (
                        <ContextMenu
                            x={contextMenu.x}
                            y={contextMenu.y}
                            onClose={() => setContextMenu({ show: false, x: 0, y: 0, deviceId: null })}
                            onDelete={handleDeleteDevice}
                            onProperties={handlePropertiesClick}
                        />
                    )}
                </div>
            )}

            {showPacketTracer && (
                <PacketTracer
                    devices={devices}
                    onClose={handleClosePacketTracer}
                />
            )}

            {notification.show && (
                <Notification
                    message={notification.message}
                    type={notification.type}
                    onClose={clearNotification}
                />
            )}

            {showProperties && selectedDeviceForProperties && (
                <PropertiesModal
                    device={selectedDeviceForProperties}
                    onClose={() => {
                        setShowProperties(false);
                        setSelectedDeviceForProperties(null);
                    }}
                    onSave={handleUpdateDeviceProperties}
                />
            )}

            {showValidationResults && (
                <ValidationResultsModal />
            )}
        </>
    );
} 