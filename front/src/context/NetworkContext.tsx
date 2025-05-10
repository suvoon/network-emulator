'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode, Dispatch, SetStateAction } from 'react';
import { DeviceType } from '@/components/DeviceIcon/types';
import { topologyApi } from '@/api/network';
import Cookies from 'js-cookie';
import { useRouter } from 'next/navigation';

export interface Device {
    id: string;
    type: DeviceType;
    x: number;
    y: number;
    name?: string;
    display_name?: string;
    ip_address?: string;
}

export interface Connection {
    id: string;
    from: string;
    to: string;
}

export interface Topology {
    id: number;
    name: string;
    description: string;
    is_active: boolean;
}

interface NetworkContextType {
    devices: Device[];
    connections: Connection[];
    showPacketTracer: boolean;
    currentTopologyId: number | undefined;
    showTopologyCreateModal: boolean;
    topologies: Topology[];
    loadingTopologies: boolean;
    topologiesError: string | null;
    setDevices: Dispatch<SetStateAction<Device[]>>;
    setConnections: Dispatch<SetStateAction<Connection[]>>;
    setShowPacketTracer: Dispatch<SetStateAction<boolean>>;
    setCurrentTopologyId: Dispatch<SetStateAction<number | undefined>>;
    setShowTopologyCreateModal: Dispatch<SetStateAction<boolean>>;
    fetchTopologies: () => Promise<void>;
    hasTopologies: boolean;
}

const NetworkContext = createContext<NetworkContextType | undefined>(undefined);

export function NetworkProvider({ children }: { children: ReactNode }) {
    const [devices, setDevices] = useState<Device[]>([]);
    const [connections, setConnections] = useState<Connection[]>([]);
    const [showPacketTracer, setShowPacketTracer] = useState(false);
    const [currentTopologyId, setCurrentTopologyId] = useState<number | undefined>(undefined);
    const [showTopologyCreateModal, setShowTopologyCreateModal] = useState(false);
    const [topologies, setTopologies] = useState<Topology[]>([]);
    const [loadingTopologies, setLoadingTopologies] = useState<boolean>(false);
    const [topologiesError, setTopologiesError] = useState<string | null>(null);
    const router = useRouter();

    const fetchTopologies = async () => {
        try {
            setLoadingTopologies(true);
            setTopologiesError(null);

            const data = await topologyApi.list();
            setTopologies(data);

            if (!currentTopologyId && data.length > 0) {
                const activeTopology = data.find((t: Topology) => t.is_active);
                if (activeTopology) {
                    setCurrentTopologyId(activeTopology.id);
                    Cookies.set('activeTopologyId', activeTopology.id.toString());
                }
            }

            return data;
        } catch (error) {
            console.error('Error fetching topologies:', error);
            if (error instanceof Error && error.message.includes('Authentication required')) {
                router.push('/auth/login');
            }
            setTopologiesError('Failed to fetch topologies');
            return [];
        } finally {
            setLoadingTopologies(false);
        }
    };

    useEffect(() => {
        fetchTopologies();
    }, []);

    return (
        <NetworkContext.Provider value={{
            devices,
            connections,
            showPacketTracer,
            currentTopologyId,
            showTopologyCreateModal,
            topologies,
            loadingTopologies,
            topologiesError,
            setDevices,
            setConnections,
            setShowPacketTracer,
            setCurrentTopologyId,
            setShowTopologyCreateModal,
            fetchTopologies,
            hasTopologies: topologies.length > 0
        }}>
            {children}
        </NetworkContext.Provider>
    );
}

export function useNetwork() {
    const context = useContext(NetworkContext);
    if (context === undefined) {
        throw new Error('useNetwork must be used within a NetworkProvider');
    }
    return context;
} 