import React from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { TabBar } from 'antd-mobile'
import AppRouter from './router'

const HIDE_TABBAR_PATHS = ['/detail/', '/compare', '/login', '/settings']

export default function App() {
  const location = useLocation()
  const navigate = useNavigate()
  const hideTabbar = HIDE_TABBAR_PATHS.some(p => location.pathname.startsWith(p))

  const tabs = [
    { key: '/', title: '首页', icon: '🏠' },
    { key: '/search', title: '搜索', icon: '🔍' },
    { key: '/map', title: '地图', icon: '🗺️' },
    { key: '/favorites', title: '收藏', icon: '⭐' },
    { key: '/profile', title: '我的', icon: '👤' },
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
