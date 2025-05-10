'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { Navbar } from '@/components';
import { useAuth } from '@/context/AuthContext';
import { materialsApi } from '@/api/network';
import parse from 'html-react-parser';
import styles from './tutorial.module.css';

interface TutorialSection {
    id: string;
    title: string;
    content: React.ReactNode;
}

interface Material {
    id: number;
    title: string;
    content: string;
    material_type: string;
    author_name: string;
    is_public: boolean;
    created_at: string;
    updated_at: string;
    groups: Array<{
        id: number;
        name: string;
    }>;
}

export default function TutorialPage() {
    const [activeSection, setActiveSection] = useState<string>('intro');
    const [educationalMaterials, setEducationalMaterials] = useState<Material[]>([]);
    const { user } = useAuth();
    const [loadingMaterials, setLoadingMaterials] = useState(false);
    const [materialsError, setMaterialsError] = useState('');
    const [isTeacher, setIsTeacher] = useState(false);
    const [selectedMaterial, setSelectedMaterial] = useState<Material | null>(null);

    const [selectedType, setSelectedType] = useState('');
    const [availableGroups, setAvailableGroups] = useState<Array<{ id: number, name: string }>>([]);

    const materialTypes = [
        { value: 'text', label: 'Текстовый материал' },
        { value: 'video', label: 'Видео' },
        { value: 'assignment', label: 'Задание' },
    ];

    useEffect(() => {
        const loadMaterials = async () => {
            if (user) {
                try {
                    setLoadingMaterials(true);
                    setMaterialsError('');

                    setIsTeacher(user.user_type === 'EDUCATOR');

                    const materials = await materialsApi.getMaterials(
                        undefined,
                        selectedType || undefined
                    );
                    setEducationalMaterials(materials);

                    if (user.user_type === 'EDUCATOR') {
                        const groups = await materialsApi.getStudentGroups();
                        setAvailableGroups(groups);
                    }
                } catch (error) {
                    console.error('Failed to load educational materials', error);
                    setMaterialsError('Не удалось загрузить учебные материалы');
                } finally {
                    setLoadingMaterials(false);
                }
            }
        };

        loadMaterials();
    }, [user, selectedType]);

    const handleDeleteMaterial = async (materialId: number) => {
        if (!confirm('Вы уверены, что хотите удалить этот материал?')) return;

        try {
            setLoadingMaterials(true);
            await materialsApi.deleteMaterial(materialId);

            const materials = await materialsApi.getMaterials(
                undefined,
                selectedType || undefined
            );
            setEducationalMaterials(materials);
            setMaterialsError('');
        } catch (err) {
            console.error('Failed to delete material', err);
            setMaterialsError('Не удалось удалить учебный материал');
        } finally {
            setLoadingMaterials(false);
        }
    };

    const handleMaterialSelect = (material: Material) => {
        setSelectedMaterial(material);
    };

    const handleBackToList = () => {
        setSelectedMaterial(null);
    };

    const tutorialSections: TutorialSection[] = [
        {
            id: 'intro',
            title: 'Введение',
            content: (
                <div>
                    <h2>Сетевой эмулятор: введение</h2>
                    <p>
                        Приветствуем вас в сетевом эмуляторе! Этот инструмент предназначен для визуального моделирования
                        и симуляции компьютерных сетей. Вы можете создавать топологии сетей, добавлять различные устройства,
                        соединять их и отслеживать прохождение пакетов.
                    </p>
                    <p>
                        Используйте меню слева для навигации по разделам руководства, чтобы изучить основные функции эмулятора.
                    </p>
                    <div className={styles.infoBox}>
                        <h4>Совет:</h4>
                        <p>Начните с создания простой топологии, добавив коммутатор и несколько хостов.</p>
                    </div>
                </div>
            )
        },
        {
            id: 'devices',
            title: 'Устройства',
            content: (
                <div>
                    <h2>Типы устройств</h2>
                    <p>
                        В эмуляторе доступны следующие типы устройств:
                    </p>
                    <ul>
                        <li>
                            <strong>Коммутатор (Switch)</strong> — устройство канального уровня, которое используется для
                            соединения различных устройств в компьютерной сети.
                        </li>
                        <li>
                            <strong>Хост (Host)</strong> — конечное устройство (компьютер, сервер), которое отправляет
                            и получает данные в сети.
                        </li>
                    </ul>
                    <h3>Как добавить устройство</h3>
                    <ol>
                        <li>Выберите нужное устройство на панели внизу экрана.</li>
                        <li>Перетащите его на рабочую область (холст).</li>
                        <li>Обратите внимание, что сначала необходимо добавить коммутатор перед добавлением хостов.</li>
                    </ol>
                    <div className={styles.warningBox}>
                        <h4>Важно:</h4>
                        <p>Хосты должны быть подключены к коммутатору, чтобы иметь возможность обмениваться данными!</p>
                    </div>
                </div>
            )
        },
        {
            id: 'connections',
            title: 'Соединения',
            content: (
                <div>
                    <h2>Создание соединений</h2>
                    <p>
                        Для создания соединения между устройствами:
                    </p>
                    <ol>
                        <li>Нажмите на первое устройство (оно будет выделено).</li>
                        <li>Затем нажмите на второе устройство для создания соединения между ними.</li>
                        <li>Линия соединения будет автоматически добавлена на схему.</li>
                    </ol>
                    <h3>Удаление соединения</h3>
                    <p>
                        Чтобы удалить соединение, просто нажмите на линию соединения между устройствами.
                        Система запросит подтверждение перед удалением.
                    </p>
                    <div className={styles.infoBox}>
                        <h4>Совет:</h4>
                        <p>Для создания полноценной сети рекомендуется сначала добавить коммутатор, затем добавить хосты и соединить их с коммутатором.</p>
                    </div>
                </div>
            )
        },
        {
            id: 'packet-tracer',
            title: 'Трассировка пакетов',
            content: (
                <div>
                    <h2>Отслеживание пакетов</h2>
                    <p>
                        Трассировка пакетов позволяет наблюдать за тем, как пакеты данных перемещаются между устройствами в вашей сети:
                    </p>
                    <ol>
                        <li>Нажмите кнопку "Трассировка пакета" в верхней панели.</li>
                        <li>В открывшемся окне выберите исходное устройство.</li>
                        <li>Выберите целевое устройство.</li>
                        <li>Выберите протокол (TCP, UDP или ICMP).</li>
                        <li>Нажмите "Запустить трассировку" для начала симуляции.</li>
                        <li>Наблюдайте, как пакет перемещается между устройствами.</li>
                    </ol>
                    <div className={styles.warningBox}>
                        <h4>Примечание:</h4>
                        <p>Для успешной трассировки пакетов необходимо, чтобы все устройства были правильно соединены и настроены.</p>
                    </div>
                </div>
            )
        },
        {
            id: 'topologies',
            title: 'Управление топологиями',
            content: (
                <div>
                    <h2>Работа с топологиями</h2>
                    <p>
                        Топология — это схема вашей сети, включающая устройства и соединения между ними.
                    </p>
                    <h3>Создание новой топологии</h3>
                    <ol>
                        <li>Нажмите на выпадающее меню топологий в верхней панели.</li>
                        <li>Выберите "Создать новую топологию".</li>
                        <li>Введите имя и описание для новой топологии.</li>
                        <li>Нажмите "Создать".</li>
                    </ol>
                    <h3>Переключение между топологиями</h3>
                    <ol>
                        <li>Откройте выпадающее меню топологий.</li>
                        <li>Выберите нужную топологию из списка.</li>
                    </ol>
                    <h3>Удаление топологии</h3>
                    <ol>
                        <li>Откройте выпадающее меню топологий.</li>
                        <li>Найдите топологию, которую хотите удалить.</li>
                        <li>Нажмите кнопку удаления рядом с ней.</li>
                    </ol>
                    <div className={styles.infoBox}>
                        <h4>Совет:</h4>
                        <p>Создавайте отдельные топологии для разных проектов или сценариев сети.</p>
                    </div>
                </div>
            )
        },
        {
            id: 'educational-materials',
            title: 'Учебные материалы',
            content: (
                <div>
                    <h2>Учебные материалы</h2>
                    {selectedMaterial ? (
                        <div className={styles.materialDetailView}>
                            <button
                                onClick={handleBackToList}
                                className={styles.backButton}
                            >
                                ← Вернуться к списку
                            </button>

                            <div className={styles.materialHeader}>
                                <h3>{selectedMaterial.title}</h3>
                                <div className={styles.materialMeta}>
                                    <span className={styles.materialType}>
                                        {materialTypes.find(t => t.value === selectedMaterial.material_type)?.label || selectedMaterial.material_type}
                                    </span>
                                    <span className={styles.materialAuthor}>Автор: {selectedMaterial.author_name}</span>
                                </div>
                            </div>

                            {selectedMaterial.groups.length > 0 && (
                                <div className={styles.materialGroups}>
                                    <span>Для групп: </span>
                                    {selectedMaterial.groups.map((group, index) => (
                                        <span key={group.id} className={styles.groupTag}>
                                            {group.name}{index < selectedMaterial.groups.length - 1 ? ', ' : ''}
                                        </span>
                                    ))}
                                </div>
                            )}

                            <div className={styles.materialContent}>
                                {selectedMaterial.material_type === 'video' ? (
                                    <div className={styles.videoEmbed}>
                                        <iframe
                                            src={selectedMaterial.content}
                                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                            allowFullScreen
                                        ></iframe>
                                    </div>
                                ) : (
                                    parse(selectedMaterial.content, {
                                        replace(domNode) {
                                            if (domNode.type === 'script') {
                                                return <></>;
                                            }
                                        },
                                    })
                                )}
                            </div>

                            <div className={styles.materialDate}>
                                Обновлено: {new Date(selectedMaterial.updated_at).toLocaleDateString()}
                            </div>
                        </div>
                    ) : (
                        <>
                            <div className={styles.filtersContainer}>
                                <div className={styles.filterGroup}>
                                    <label htmlFor="typeFilter" className={styles.filterLabel}>Тип материала:</label>
                                    <select
                                        id="typeFilter"
                                        value={selectedType}
                                        onChange={(e) => setSelectedType(e.target.value)}
                                        className={styles.formSelect}
                                    >
                                        <option value="">Все типы</option>
                                        {materialTypes.map(type => (
                                            <option key={type.value} value={type.value}>{type.label}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            {materialsError && (
                                <div className={styles.errorBox}>
                                    <p>{materialsError}</p>
                                </div>
                            )}

                            <div className={styles.materialsScrollContainer}>
                                {loadingMaterials ? (
                                    <p>Загрузка материалов...</p>
                                ) : educationalMaterials.length === 0 ? (
                                    <div className={styles.emptyState}>
                                        <p>Нет доступных учебных материалов.</p>
                                    </div>
                                ) : (
                                    <ul className={styles.materialsList}>
                                        {educationalMaterials.map(material => (
                                            <li key={material.id} className={styles.materialItem}>
                                                <div
                                                    className={styles.materialListItem}
                                                    onClick={() => handleMaterialSelect(material)}
                                                >
                                                    <div className={styles.materialHeader}>
                                                        <h3>{material.title}</h3>
                                                        <div className={styles.materialMeta}>
                                                            <span className={styles.materialType}>
                                                                {materialTypes.find(t => t.value === material.material_type)?.label || material.material_type}
                                                            </span>
                                                            <span className={styles.materialAuthor}>Автор: {material.author_name}</span>
                                                            {isTeacher && (
                                                                <button
                                                                    onClick={(e) => {
                                                                        e.stopPropagation();
                                                                        handleDeleteMaterial(material.id);
                                                                    }}
                                                                    className={styles.deleteButton}
                                                                    title="Удалить материал"
                                                                >
                                                                    ✕
                                                                </button>
                                                            )}
                                                        </div>
                                                    </div>

                                                    {material.groups.length > 0 && (
                                                        <div className={styles.materialGroups}>
                                                            <span>Для групп: </span>
                                                            {material.groups.map((group, index) => (
                                                                <span key={group.id} className={styles.groupTag}>
                                                                    {group.name}{index < material.groups.length - 1 ? ', ' : ''}
                                                                </span>
                                                            ))}
                                                        </div>
                                                    )}

                                                    <div className={styles.materialPreview}>
                                                        {material.material_type === 'video' ? (
                                                            <span>Видеоматериал - нажмите, чтобы просмотреть</span>
                                                        ) : (
                                                            <div className={styles.contentPreview}>
                                                                {material.content.substring(0, 150)}
                                                                {material.content.length > 150 ? '...' : ''}
                                                            </div>
                                                        )}
                                                    </div>

                                                    <div className={styles.materialDate}>
                                                        Обновлено: {new Date(material.updated_at).toLocaleDateString()}
                                                    </div>
                                                </div>
                                            </li>
                                        ))}
                                    </ul>
                                )}
                            </div>
                        </>
                    )}
                </div>
            )
        }
    ];

    return (
        <div className={styles.container}>
            <Navbar />
            <div className={styles.tutorialContent}>
                <div className={styles.sidebar}>
                    <h3>Руководства</h3>
                    <ul>
                        {tutorialSections.map(tutorial => (
                            <li
                                key={tutorial.id}
                                className={activeSection === tutorial.id ? styles.active : ''}
                                onClick={() => setActiveSection(tutorial.id)}
                            >
                                {tutorial.title}
                            </li>
                        ))}
                    </ul>
                    <div className={styles.backLink}>
                        <Link href="/">← Вернуться к эмулятору</Link>
                    </div>
                </div>
                <div className={styles.content}>
                    {tutorialSections.find(t => t.id === activeSection)?.content}
                </div>
            </div>
        </div>
    );
} 