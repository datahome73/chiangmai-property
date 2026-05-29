import React, { Suspense, lazy } from 'react'
import { Routes, Route } from 'react-router-dom'

const HomePage = lazy(() => import('../pages/HomePage'))
const SearchPage = lazy(() => import('../pages/SearchPage'))
const DetailPage = lazy(() => import('../pages/DetailPage'))
const MapPage = lazy(() => import('../pages/MapPage'))
const ComparePage = lazy(() => import('../pages/ComparePage'))
const FavoritesPage = lazy(() => import('../pages/FavoritesPage'))
const LoginPage = lazy(() => import('../pages/LoginPage'))
const ProfilePage = lazy(() => import('../pages/ProfilePage'))
const SettingsPage = lazy(() => import('../pages/SettingsPage'))

function Loading() {
  return <div style={{ padding: 40, textAlign: 'center', color: '#999' }}>加载中...</div>
}

export default function AppRouter() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/detail/:id" element={<DetailPage />} />
        <Route path="/map" element={<MapPage />} />
        <Route path="/compare" element={<ComparePage />} />
        <Route path="/favorites" element={<FavoritesPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Suspense>
  )
}
