'use client';

import styles from "./page.module.css";
import { Canvas, DevicesPanel, Navbar } from "@/components";
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push('/auth/login');
    }
  }, [user, loading, router]);

  if (loading) {
    return <div className={styles.loading}>Загрузка...</div>;
  }

  if (!user) {
    return null;
  }

  return (
    <div className={styles.container}>
      <Navbar />
      <main className={styles.main}>
        <Canvas />
      </main>
      <DevicesPanel />
    </div>
  );
}
