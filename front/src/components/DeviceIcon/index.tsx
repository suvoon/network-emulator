'use client';

import styles from './DeviceIcon.module.css';

export const icons = {
    router: (
        <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" fill="none">
            <path d="M4 6h16M4 12h16M4 18h16" strokeWidth="2" strokeLinecap="round" />
        </svg>
    ),
    switch: (
        <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" fill="none">
            <rect x="2" y="2" width="20" height="20" rx="2" strokeWidth="2" />
            <path d="M7 8h10M7 12h10M7 16h10" strokeWidth="2" strokeLinecap="round" />
        </svg>
    ),
    host: (
        <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" fill="none">
            <rect x="2" y="3" width="20" height="14" rx="2" strokeWidth="2" />
            <path d="M8 21h8M12 17v4" strokeWidth="2" strokeLinecap="round" />
        </svg>
    ),
    server: (
        <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" fill="none">
            <rect x="2" y="2" width="20" height="20" rx="2" strokeWidth="2" />
            <path d="M4 8h16M4 16h16" strokeWidth="2" strokeLinecap="round" />
            <circle cx="8" cy="12" r="1" fill="currentColor" />
            <circle cx="8" cy="20" r="1" fill="currentColor" />
            <circle cx="8" cy="4" r="1" fill="currentColor" />
        </svg>
    ),
};

interface DeviceIconProps {
    type: keyof typeof icons;
    displayName?: string;
    isSelected?: boolean;
}

export function DeviceIcon({ type, displayName, isSelected = false }: DeviceIconProps) {
    return (
        <div className={`${styles.deviceIcon} ${isSelected ? styles.selected : ''}`}>
            <div className={styles.iconWrapper}>
                {icons[type] || null}
            </div>
            {displayName && <div className={styles.deviceName}>{displayName}</div>}
        </div>
    );
} 