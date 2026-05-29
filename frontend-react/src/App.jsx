import React from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { TabBar } from 'antd-mobile'
import { useTranslation } from './i18n'
import AppRouter from './router'

const HIDE_TABBAR_PATHS = ['/detail/', '/compare', '/login', '/settings']

export default function App() {
  const location = useLocation()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const hideTabbar = HIDE_TABBAR_PATHS.some(p => location.pathname.startsWith(p))

  const tabs = [
    { key: '/', title: t('tabHome'), icon: '🏠' },
    { key: '/search', title: t('tabSearch'), icon: '🔍' },
    { key: '/map', title: t('tabMap'), icon: '🗺️' },
    { key: '/favorites', title: t('tabFavorites'), icon: '⭐' },
    { key: '/profile', title: t('tabProfile'), icon: '👤' },
  ]

  return (
    <div className="app-container">
      <div className={`app-content ${hideTabbar ? 'no-tabbar' : ''}`}>
        <AppRouter />
      </div>
      {!hideTabbar && (
        <TabBar
          activeKey={location.pathname}
          onChange={(key) => navigate(key)}
          safeArea
        >
          {tabs.map((tab) => (
            <TabBar.Item key={tab.key} icon={tab.icon} title={tab.title} />
          ))}
        </TabBar>
      )}
    </div>
  )
}
