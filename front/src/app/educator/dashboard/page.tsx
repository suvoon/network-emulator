'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../../context/AuthContext';
import styles from './dashboard.module.css';
import { materialsApi, authApi } from '../../../api/network';
import { Navbar } from '../../../components/Navbar';

interface Student {
    id: number;
    username: string;
    email: string;
}

interface Group {
    id: number;
    name: string;
    description: string;
    student_count: number;
    members: Student[];
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
    groups: Group[];
}

export default function EducatorDashboard() {
    const { user } = useAuth();
    const router = useRouter();
    const [activeTab, setActiveTab] = useState('groups');

    const [groups, setGroups] = useState<Group[]>([]);
    const [newGroup, setNewGroup] = useState({ name: '', description: '' });
    const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);

    const [materials, setMaterials] = useState<Material[]>([]);
    const [newMaterial, setNewMaterial] = useState({
        title: '',
        content: '',
        material_type: 'text',
        is_public: false,
        group_ids: [] as number[]
    });

    const [studentUsername, setStudentUsername] = useState('');
    const [allUsers, setAllUsers] = useState<Student[]>([]);
    const [searchTerm, setSearchTerm] = useState('');

    useEffect(() => {
        if (user && user.user_type !== 'EDUCATOR') {
            router.push('/');
        }
    }, [user, router]);

    useEffect(() => {
        if (user?.user_type === 'EDUCATOR') {
            fetchGroups();
            fetchMaterials();
            fetchAllUsers();
        }
    }, [user]);

    const fetchGroups = async () => {
        try {
            const groups = await materialsApi.getStudentGroups();
            setGroups(groups);
        } catch (error) {
            console.error('Error fetching groups:', error);
        }
    };

    const fetchMaterials = async () => {
        try {
            const materials = await materialsApi.getMaterials();
            setMaterials(materials);
        } catch (error) {
            console.error('Error fetching materials:', error);
        }
    };

    const fetchAllUsers = async () => {
        try {
            const users = await authApi.getUsers();
            setAllUsers(users);
        } catch (error) {
            console.error('Error fetching users:', error);
        }
    };

    const handleCreateGroup = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newGroup.name.trim()) return;

        try {
            await materialsApi.createStudentGroup(newGroup);
            fetchGroups();
            setNewGroup({ name: '', description: '' });
        } catch (error) {
            console.error('Error creating group:', error);
        }
    };

    const handleCreateMaterial = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newMaterial.title.trim() || !newMaterial.content.trim()) return;

        try {
            await materialsApi.createMaterial({
                title: newMaterial.title,
                content: newMaterial.content,
                material_type: newMaterial.material_type,
                is_public: newMaterial.is_public,
                group_ids: newMaterial.group_ids
            });

            fetchMaterials();
            setNewMaterial({
                title: '',
                content: '',
                material_type: 'text',
                is_public: false,
                group_ids: []
            });
        } catch (error) {
            console.error('Error creating material:', error);
            alert('Failed to create material. Please try again.');
        }
    };

    const handleAddStudent = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedGroup || !studentUsername.trim()) return;

        try {
            const student = allUsers.find(u => u.username === studentUsername);
            if (!student) {
                alert('Пользователь не найден');
                return;
            }

            await materialsApi.addStudentToGroup(selectedGroup.id, student.id);
            fetchGroups();
            setStudentUsername('');

            if (selectedGroup) {
                const updatedGroup = await materialsApi.getStudentGroup(selectedGroup.id);
                setSelectedGroup(updatedGroup);
            }
        } catch (error) {
            console.error('Error adding student to group:', error);
        }
    };

    const handleRemoveStudent = async (studentId: number) => {
        if (!selectedGroup) return;

        try {
            await materialsApi.removeStudentFromGroup(selectedGroup.id, studentId);

            const updatedMembers = selectedGroup.members.filter(member => member.id !== studentId);
            setSelectedGroup({
                ...selectedGroup,
                members: updatedMembers,
                student_count: updatedMembers.length
            });
            fetchGroups();
        } catch (error) {
            console.error('Error removing student from group:', error);
        }
    };

    const filteredUsers = allUsers.filter(user =>
        user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
        user.email.toLowerCase().includes(searchTerm.toLowerCase())
    );

    if (!user || user.user_type !== 'EDUCATOR') {
        return <div className={styles.loading}>Загрузка...</div>;
    }

    return (
        <div className={styles.dashboardContainer}>
            <Navbar isDashboardPage={true} />

            <div className={styles.tabsContainer}>
                <button
                    className={`${styles.tabButton} ${activeTab === 'groups' ? styles.activeTab : ''}`}
                    onClick={() => setActiveTab('groups')}
                >
                    Группы
                </button>
                <button
                    className={`${styles.tabButton} ${activeTab === 'materials' ? styles.activeTab : ''}`}
                    onClick={() => setActiveTab('materials')}
                >
                    Учебные материалы
                </button>
            </div>

            {activeTab === 'groups' && (
                <div className={styles.tabContent}>
                    <div className={styles.twoColumnLayout}>
                        <div className={styles.leftColumn}>
                            <h2>Список групп</h2>
                            <div className={styles.groupsList}>
                                {groups.length === 0 ? (
                                    <p>Нет доступных групп</p>
                                ) : (
                                    groups.map(group => (
                                        <div
                                            key={group.id}
                                            className={`${styles.groupItem} ${selectedGroup?.id === group.id ? styles.selectedGroup : ''}`}
                                            onClick={() => setSelectedGroup(group)}
                                        >
                                            <h3>{group.name}</h3>
                                            <p>{group.description}</p>
                                            <span className={styles.studentCount}>
                                                Студентов: {group.student_count}
                                            </span>
                                        </div>
                                    ))
                                )}
                            </div>

                            <div className={styles.createForm}>
                                <h3>Создать новую группу</h3>
                                <form onSubmit={handleCreateGroup}>
                                    <input
                                        type="text"
                                        placeholder="Название группы"
                                        value={newGroup.name}
                                        onChange={(e) => setNewGroup({ ...newGroup, name: e.target.value })}
                                        required
                                        className={styles.formInput}
                                    />
                                    <textarea
                                        placeholder="Описание группы"
                                        value={newGroup.description}
                                        onChange={(e) => setNewGroup({ ...newGroup, description: e.target.value })}
                                        className={styles.formTextarea}
                                    />
                                    <button type="submit" className={styles.formButton}>
                                        Создать группу
                                    </button>
                                </form>
                            </div>
                        </div>

                        <div className={styles.rightColumn}>
                            {selectedGroup ? (
                                <>
                                    <h2>Управление группой: {selectedGroup.name}</h2>

                                    <div className={styles.groupDetails}>
                                        <h3>Описание</h3>
                                        <p>{selectedGroup.description || 'Нет описания'}</p>

                                        <h3>Участники группы</h3>
                                        {selectedGroup.members && selectedGroup.members.length > 0 ? (
                                            <div className={styles.membersList}>
                                                {selectedGroup.members.map(student => (
                                                    <div key={student.id} className={styles.memberItem}>
                                                        <div>
                                                            <span className={styles.memberName}>{student.username}</span>
                                                            <span className={styles.memberEmail}>{student.email}</span>
                                                        </div>
                                                        <button
                                                            className={styles.removeButton}
                                                            onClick={() => handleRemoveStudent(student.id)}
                                                        >
                                                            Удалить
                                                        </button>
                                                    </div>
                                                ))}
                                            </div>
                                        ) : (
                                            <p>В группе нет студентов</p>
                                        )}

                                        <div className={styles.addStudentForm}>
                                            <h3>Добавить студента</h3>
                                            <form onSubmit={handleAddStudent}>
                                                <input
                                                    type="text"
                                                    placeholder="Имя пользователя"
                                                    value={studentUsername}
                                                    onChange={(e) => setStudentUsername(e.target.value)}
                                                    required
                                                    className={styles.formInput}
                                                />
                                                <button type="submit" className={styles.formButton}>
                                                    Добавить
                                                </button>
                                            </form>

                                            <div className={styles.userSearch}>
                                                <h4>Поиск пользователей</h4>
                                                <input
                                                    type="text"
                                                    placeholder="Поиск по имени или email"
                                                    value={searchTerm}
                                                    onChange={(e) => setSearchTerm(e.target.value)}
                                                    className={styles.formInput}
                                                />

                                                <div className={styles.searchResults}>
                                                    {searchTerm && filteredUsers.slice(0, 5).map(user => (
                                                        <div
                                                            key={user.id}
                                                            className={styles.searchResultItem}
                                                            onClick={() => setStudentUsername(user.username)}
                                                        >
                                                            <span>{user.username}</span>
                                                            <span className={styles.smallText}>{user.email}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </>
                            ) : (
                                <div className={styles.noSelection}>
                                    <p>Выберите группу из списка слева для управления</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {activeTab === 'materials' && (
                <div className={styles.tabContent}>
                    <div className={styles.twoColumnLayout}>
                        <div className={styles.leftColumn}>
                            <h2>Список материалов</h2>
                            <div className={styles.materialsList}>
                                {materials.length === 0 ? (
                                    <p>Нет доступных материалов</p>
                                ) : (
                                    materials.map(material => (
                                        <div key={material.id} className={styles.materialItem}>
                                            <h3>{material.title}</h3>
                                            <div className={styles.materialMeta}>
                                                <span className={styles.materialType}>
                                                    {material.material_type === 'text' ? 'Текстовый материал' :
                                                        material.material_type === 'video' ? 'Видео' :
                                                            material.material_type === 'assignment' ? 'Задание' :
                                                                material.material_type}
                                                </span>
                                                <span className={styles.materialVisibility}>
                                                    {material.is_public ? 'Открытый' : 'Закрытый'}
                                                </span>
                                            </div>
                                            <div className={styles.materialGroups}>
                                                {material.groups && material.groups.length > 0 ? (
                                                    <>
                                                        <small>Доступно группам:</small>
                                                        <div className={styles.groupTags}>
                                                            {material.groups.map(group => (
                                                                <span key={group.id} className={styles.groupTag}>
                                                                    {group.name}
                                                                </span>
                                                            ))}
                                                        </div>
                                                    </>
                                                ) : (
                                                    <small>Не привязан к группам</small>
                                                )}
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        <div className={styles.rightColumn}>
                            <div className={styles.createForm}>
                                <h2>Создать новый материал</h2>
                                <form onSubmit={handleCreateMaterial}>
                                    <input
                                        type="text"
                                        placeholder="Заголовок"
                                        value={newMaterial.title}
                                        onChange={(e) => setNewMaterial({ ...newMaterial, title: e.target.value })}
                                        required
                                        className={styles.formInput}
                                    />

                                    <div className={styles.formRow}>
                                        <div className={styles.formGroup}>
                                            <label>Тип материала</label>
                                            <select
                                                value={newMaterial.material_type}
                                                onChange={(e) => setNewMaterial({ ...newMaterial, material_type: e.target.value })}
                                                className={styles.formSelect}
                                            >
                                                <option value="text">Текстовый материал</option>
                                                <option value="video">Видео</option>
                                                <option value="assignment">Задание</option>
                                            </select>
                                        </div>

                                        <div className={`${styles.formGroup} ${styles.checkboxGroup}`}>
                                            <label className={styles.checkboxLabel}>
                                                <input
                                                    type="checkbox"
                                                    checked={newMaterial.is_public}
                                                    onChange={(e) => setNewMaterial({ ...newMaterial, is_public: e.target.checked })}
                                                />
                                                Открытый материал
                                            </label>
                                        </div>
                                    </div>

                                    <div className={styles.formGroup}>
                                        <label>Доступен для групп</label>
                                        <div className={styles.groupCheckboxes}>
                                            {groups.map(group => (
                                                <label key={group.id} className={styles.checkboxLabel}>
                                                    <input
                                                        type="checkbox"
                                                        checked={newMaterial.group_ids.includes(group.id)}
                                                        onChange={(e) => {
                                                            const groupIds = [...newMaterial.group_ids];
                                                            if (e.target.checked) {
                                                                groupIds.push(group.id);
                                                            } else {
                                                                const index = groupIds.indexOf(group.id);
                                                                if (index > -1) {
                                                                    groupIds.splice(index, 1);
                                                                }
                                                            }
                                                            setNewMaterial({ ...newMaterial, group_ids: groupIds });
                                                        }}
                                                    />
                                                    {group.name}
                                                </label>
                                            ))}
                                        </div>
                                    </div>

                                    <textarea
                                        placeholder="Содержание материала (поддерживается Markdown)"
                                        value={newMaterial.content}
                                        onChange={(e) => setNewMaterial({ ...newMaterial, content: e.target.value })}
                                        required
                                        className={`${styles.formTextarea} ${styles.contentTextarea}`}
                                        rows={10}
                                    />

                                    <button type="submit" className={styles.formButton}>
                                        Создать материал
                                    </button>
                                </form>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
} 