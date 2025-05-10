'use client';

import styles from './Connector.module.css';

interface ConnectorProps {
    startX: number;
    startY: number;
    endX: number;
    endY: number;
    isSelected?: boolean;
    onClick?: () => void;
}

export function Connector({ startX, startY, endX, endY, isSelected, onClick }: ConnectorProps) {
    const length = Math.sqrt(Math.pow(endX - startX, 2) + Math.pow(endY - startY, 2));
    const angle = Math.atan2(endY - startY, endX - startX) * 180 / Math.PI;

    return (
        <div
            className={`${styles.connector} ${isSelected ? styles.selected : ''}`}
            style={{
                left: startX,
                top: startY,
                width: length,
                transform: `rotate(${angle}deg)`,
                transformOrigin: '0 50%',
            }}
            onClick={onClick}
        />
    );
} 