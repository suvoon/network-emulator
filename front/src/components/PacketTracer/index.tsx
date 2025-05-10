'use client';

import { useState, useEffect } from 'react';
import styles from './PacketTracer.module.css';
import { packetApi } from '@/api/network';
import { useRouter } from 'next/navigation';

interface PacketTracerProps {
    devices: Array<{
        id: string;
        name?: string;
        type: string;
        display_name?: string;
        ip_address?: string;
    }>;
    onClose: () => void;
}

interface TraceResult {
    id: number;
    source_node: string;
    destination_node: string;
    state: string;
    current_node: string;
    route: string[];
    hops: Array<{
        node: string;
        time: number;
        action: string;
        details: string;
    }>;
    completed: boolean;
    success: boolean;
    error: string | null;
}

interface PingResult {
    source: string;
    source_ip: string;
    destination_ip: string;
    packets_sent: number;
    packets_received: number;
    packet_loss: number;
    results: Array<{
        seq: number;
        success: boolean;
        time_ms?: number;
        error?: string;
    }>;
}

type ToolType = 'trace' | 'ping';

export function PacketTracer({ devices, onClose }: PacketTracerProps) {
    const [source, setSource] = useState('');
    const [destination, setDestination] = useState('');
    const [destinationIp, setDestinationIp] = useState('');
    const [protocol, setProtocol] = useState('tcp');
    const [traceResult, setTraceResult] = useState<TraceResult | null>(null);
    const [pingResult, setPingResult] = useState<PingResult | null>(null);
    const [traceId, setTraceId] = useState<number | null>(null);
    const [polling, setPolling] = useState(false);
    const [pingCount, setPingCount] = useState(4);
    const [selectedTool, setSelectedTool] = useState<ToolType>('trace');
    const [isRunning, setIsRunning] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const router = useRouter();

    useEffect(() => {
        if (destination) {
            const selectedDevice = devices.find(d => d.id === destination);
            if (selectedDevice && selectedDevice.ip_address) {
                const ipWithoutMask = selectedDevice.ip_address.includes('/')
                    ? selectedDevice.ip_address.split('/')[0]
                    : selectedDevice.ip_address;
                setDestinationIp(ipWithoutMask);
            }
        }
    }, [destination, devices]);

    const handleTrace = async () => {
        try {
            setIsRunning(true);
            setTraceResult(null);
            setError(null);

            const data = await packetApi.startTrace({
                source_node: source,
                destination_node: destination,
                packet_config: {
                    protocol,
                    ip: {
                        ttl: 64
                    },
                    [protocol]: {
                        sport: 0,
                        dport: 0
                    }
                },
            });

            setTraceId(data.trace_id);
            setPolling(true);
        } catch (error) {
            console.error('Error starting trace:', error);
            if (error instanceof Error && error.message.includes('Authentication required')) {
                router.push('/auth/login');
            } else {
                setError(error instanceof Error ? error.message : 'Failed to start packet trace');
            }
            setIsRunning(false);
        }
    };

    const handlePing = async () => {
        try {
            setIsRunning(true);
            setPingResult(null);
            setError(null);

            const results = await packetApi.ping({
                source_node: source,
                destination_ip: destinationIp,
                count: pingCount
            });

            setPingResult(results);
            setIsRunning(false);
        } catch (error) {
            console.error('Error running ping:', error);
            if (error instanceof Error && error.message.includes('Authentication required')) {
                router.push('/auth/login');
            } else {
                setError(error instanceof Error ? error.message : 'Failed to ping destination');
            }
            setIsRunning(false);
        }
    };

    useEffect(() => {
        let pollInterval: NodeJS.Timeout;

        const pollTrace = async () => {
            if (traceId && polling) {
                try {
                    const data = await packetApi.getTrace(traceId);
                    setTraceResult(data);

                    if (data.completed || data.error) {
                        setPolling(false);
                        setIsRunning(false);
                    }
                } catch (error) {
                    console.error('Error polling trace:', error);
                    if (error instanceof Error && error.message.includes('Authentication required')) {
                        router.push('/auth/login');
                    } else {
                        setError(error instanceof Error ? error.message : 'Failed to get trace results');
                    }
                    setPolling(false);
                    setIsRunning(false);
                }
            }
        };

        if (polling) {
            pollInterval = setInterval(pollTrace, 1000);
        }

        return () => {
            if (pollInterval) {
                clearInterval(pollInterval);
            }
        };
    }, [traceId, polling, router]);

    const formatTraceResults = (result: TraceResult) => {
        return (
            <div>
                <div>Статус: {result.completed ? (result.success ? 'Успешно' : 'Неудачно') : 'В процессе'}</div>
                <div>Текущий узел: {result.current_node}</div>
                {result.error && <div className={styles.error}>Ошибка: {result.error}</div>}
                <div>Переходы:</div>
                <ul className={styles.hopsList}>
                    {result.hops.map((hop, index) => (
                        <li key={index} className={styles.hopItem}>
                            <span className={styles.hopNode}>{hop.node}</span>
                            <span className={styles.hopAction}>{hop.action}</span>
                            {hop.details && <span className={styles.hopDetails}>{hop.details}</span>}
                        </li>
                    ))}
                </ul>
            </div>
        );
    };

    const formatPingResults = (result: PingResult) => {
        return (
            <div>
                <div className={styles.pingHeader}>
                    <div>Пинг от {result.source} ({result.source_ip}) к {result.destination_ip}</div>
                    <div>Отправлено: {result.packets_sent}, Получено: {result.packets_received}, Потери: {result.packet_loss.toFixed(1)}%</div>
                </div>
                <ul className={styles.pingList}>
                    {result.results.map((ping, index) => (
                        <li key={index} className={styles.pingItem}>
                            {ping.success ? (
                                <span>
                                    Ответ от {result.destination_ip}: последовательность={ping.seq} время={ping.time_ms?.toFixed(2)}мс
                                </span>
                            ) : (
                                <span className={styles.error}>
                                    Ошибка последовательности {ping.seq}: {ping.error}
                                </span>
                            )}
                        </li>
                    ))}
                </ul>
            </div>
        );
    };

    return (
        <div className={styles.modalOverlay}>
            <div className={styles.container}>
                <div className={styles.header}>
                    <h2 className={styles.title}>Трассировка пакетов</h2>
                    <button className={styles.closeButton} onClick={onClose}>×</button>
                </div>

                <div className={styles.toolSelector}>
                    <button
                        className={`${styles.toolButton} ${selectedTool === 'trace' ? styles.active : ''}`}
                        onClick={() => setSelectedTool('trace')}
                    >
                        Трассировка
                    </button>
                    <button
                        className={`${styles.toolButton} ${selectedTool === 'ping' ? styles.active : ''}`}
                        onClick={() => setSelectedTool('ping')}
                    >
                        Пинг
                    </button>
                </div>

                {error && (
                    <div className={styles.error}>
                        {error}
                    </div>
                )}

                <div className={styles.content}>
                    <div className={styles.form}>
                        <div className={styles.formGroup}>
                            <label className={styles.label}>Исходное устройство</label>
                            <select
                                className={styles.select}
                                value={source}
                                onChange={e => setSource(e.target.value)}
                                disabled={isRunning}
                            >
                                <option value="">Выберите исходное устройство</option>
                                {devices.filter(d => d.type === 'host').map(device => (
                                    <option key={device.id} value={device.id}>
                                        {device.display_name || device.name || device.id}
                                        {device.ip_address ? ` (${device.ip_address})` : ''}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {selectedTool === 'trace' ? (
                            <>
                                <div className={styles.formGroup}>
                                    <label className={styles.label}>Целевое устройство</label>
                                    <select
                                        className={styles.select}
                                        value={destination}
                                        onChange={e => setDestination(e.target.value)}
                                        disabled={isRunning}
                                    >
                                        <option value="">Выберите целевое устройство</option>
                                        {devices.filter(d => d.type === 'host').map(device => (
                                            <option key={device.id} value={device.id}>
                                                {device.display_name || device.name || device.id}
                                                {device.ip_address ? ` (${device.ip_address})` : ''}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <div className={styles.formGroup}>
                                    <label className={styles.label}>Протокол</label>
                                    <select
                                        className={styles.select}
                                        value={protocol}
                                        onChange={e => setProtocol(e.target.value)}
                                        disabled={isRunning}
                                    >
                                        <option value="tcp">TCP</option>
                                        <option value="udp">UDP</option>
                                        <option value="icmp">ICMP</option>
                                    </select>
                                </div>
                            </>
                        ) : (
                            <>
                                <div className={styles.formGroup}>
                                    <label className={styles.label}>IP назначения</label>
                                    <div className={styles.ipInputGroup}>
                                        <input
                                            type="text"
                                            className={styles.ipInput}
                                            value={destinationIp}
                                            onChange={e => setDestinationIp(e.target.value)}
                                            placeholder="Введите IP (например, 10.0.0.2)"
                                            disabled={isRunning}
                                        />
                                        <select
                                            className={styles.ipSelect}
                                            onChange={e => {
                                                const selectedId = e.target.value;
                                                if (selectedId) {
                                                    const selectedDevice = devices.find(d => d.id === selectedId);
                                                    if (selectedDevice && selectedDevice.ip_address) {
                                                        const ipWithoutMask = selectedDevice.ip_address.includes('/')
                                                            ? selectedDevice.ip_address.split('/')[0]
                                                            : selectedDevice.ip_address;
                                                        setDestinationIp(ipWithoutMask);
                                                    }
                                                }
                                            }}
                                            disabled={isRunning}
                                        >
                                            <option value="">Выбрать устройство</option>
                                            {devices.filter(d => d.ip_address).map(device => (
                                                <option key={device.id} value={device.id}>
                                                    {device.display_name || device.name || device.id}
                                                    {device.ip_address ? ` (${device.ip_address})` : ''}
                                                </option>
                                            ))}
                                        </select>
                                    </div>
                                </div>

                                <div className={styles.formGroup}>
                                    <label className={styles.label}>Количество пакетов</label>
                                    <input
                                        type="number"
                                        min="1"
                                        max="10"
                                        className={styles.numberInput}
                                        value={pingCount}
                                        onChange={e => setPingCount(Math.min(10, Math.max(1, parseInt(e.target.value) || 1)))}
                                        disabled={isRunning}
                                    />
                                </div>
                            </>
                        )}

                        <button
                            className={styles.menuButton}
                            onClick={selectedTool === 'trace' ? handleTrace : handlePing}
                            disabled={!source || (selectedTool === 'trace' ? !destination : !destinationIp) || isRunning}
                        >
                            {isRunning ? 'Выполняется...' : (selectedTool === 'trace' ? 'Запустить трассировку' : 'Запустить пинг')}
                        </button>

                        {traceResult && selectedTool === 'trace' && (
                            <div className={styles.results}>
                                {formatTraceResults(traceResult)}
                            </div>
                        )}

                        {pingResult && selectedTool === 'ping' && (
                            <div className={styles.results}>
                                {formatPingResults(pingResult)}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
} 