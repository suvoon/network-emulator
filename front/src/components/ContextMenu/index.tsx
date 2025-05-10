'use client';

import { useEffect, useRef } from 'react';
import styles from './ContextMenu.module.css';

interface ContextMenuProps {
    x: number;
    y: number;
    onClose: () => void;
    onDelete: () => void;
    onProperties: () => void;
}

export function ContextMenu({ x, y, onClose, onDelete, onProperties }: ContextMenuProps) {
    const menuRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                onClose();
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [onClose]);

    return (
        <div
            className={styles.contextMenu}
            style={{ left: x, top: y }}
            ref={menuRef}
        >
            <button onClick={onProperties}>Свойства</button>
            <button onClick={onDelete}>Удалить</button>
        </div>
    );
} 