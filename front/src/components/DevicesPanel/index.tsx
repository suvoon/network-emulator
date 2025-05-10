'use client';

import { useState } from 'react';
import styles from './DevicesPanel.module.css';
import { DeviceIcon } from '../DeviceIcon';
import { DeviceType } from '../DeviceIcon/types';
import { useNetwork } from '../../context/NetworkContext';

export function DevicesPanel() {
    const [hoveredDevice, setHoveredDevice] = useState<string | null>(null);
    const { devices } = useNetwork();

    const hasSwitches = devices.some(device => device.type === 'switch');

    const handleDragStart = (e: React.DragEvent, deviceType: DeviceType) => {
        e.dataTransfer.setData('deviceType', deviceType);
        e.dataTransfer.effectAllowed = 'copy';
    };

    const handleMouseEnter = (deviceType: string) => {
        setHoveredDevice(deviceType);
    };

    const handleMouseLeave = () => {
        setHoveredDevice(null);
    };

    return (
        <div className={styles.panel}>
            <div className={styles.header}>Устройства</div>
            <div className={styles.devices}>
                <div
                    className={styles.device}
                    draggable
                    onDragStart={(e) => handleDragStart(e, 'switch')}
                    onMouseEnter={() => handleMouseEnter('switch')}
                    onMouseLeave={handleMouseLeave}
                >
                    <div className={styles.deviceIcon}>
                        <DeviceIcon type="switch" />
                    </div>
                    <div className={styles.deviceName}>Коммутатор</div>
                </div>
                <div
                    className={styles.device}
                    draggable
                    onDragStart={(e) => handleDragStart(e, 'host')}
                    onMouseEnter={() => handleMouseEnter('host')}
                    onMouseLeave={handleMouseLeave}
                >
                    <div className={styles.deviceIcon}>
                        <DeviceIcon type="host" />
                    </div>
                    <div className={styles.deviceName}>Хост</div>
                </div>
                <div
                    className={styles.device}
                    draggable
                    onDragStart={(e) => handleDragStart(e, 'router')}
                    onMouseEnter={() => handleMouseEnter('router')}
                    onMouseLeave={handleMouseLeave}
                >
                    <div className={styles.deviceIcon}>
                        <DeviceIcon type="router" />
                    </div>
                    <div className={styles.deviceName}>Роутер</div>
                </div>
            </div>

            {!hasSwitches && (
                <div className={styles.notice}>
                    <p>Сначала добавьте коммутатор, затем хосты</p>
                </div>
            )}

            {hoveredDevice && (
                <div className={styles.tooltip}>
                    {hoveredDevice === 'switch' && (
                        <div>
                            <h3>Коммутатор</h3>
                            <p>Устройство для соединения компьютеров в сеть.</p>
                        </div>
                    )}
                    {hoveredDevice === 'host' && (
                        <div>
                            <h3>Хост</h3>
                            <p>Компьютер или устройство в сети.</p>
                            {!hasSwitches && (
                                <p className={styles.warning}>Необходимо сначала добавить коммутатор!</p>
                            )}
                        </div>
                    )}
                    {hoveredDevice === 'router' && (
                        <div>
                            <h3>Роутер</h3>
                            <p>Устройство для соединения разных сетей и маршрутизации пакетов между ними.</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
} 