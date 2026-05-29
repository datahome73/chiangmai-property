import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { NavBar, List, Button, ActionSheet, Toast } from 'antd-mobile'
import { clearAuthHeader } from '../api'
import useUserStore from '../stores/userStore'
import { useTranslation } from '../i18n'

const languageActions = [
  { key: 'zh', text: '中文' },
  { key: 'en', text: 'English' },
  { key: 'th', text: 'ภาษาไทย' },
]

export default function SettingsPage() {
  const navigate = useNavigate()
  const { logout } = useUserStore()
  const { t, lang, setLanguage } = useTranslation()
  const [actionSheetVisible, setActionSheetVisible] = useState(false)

  const langLabels = { zh: '中文', en: 'English', th: 'ภาษาไทย' }

  const handleLanguageSelect = (item) => {
    setLanguage(item.key)
    setActionSheetVisible(false)
    Toast.show({ icon: 'success', content: langLabels[item.key] })
  }

  const handleLogout = () => {
    ActionSheet.show({
      actions: [{ key: 'confirm', text: t('confirmLogout'), danger: true }],
      onAction: (item) => {
        if (item.key === 'confirm') {
          clearAuthHeader()
          logout()
          Toast.show(t('loggedOut'))
          navigate('/profile')
        }
      },
    })
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
      <NavBar onBack={() => navigate(-1)}>{t('settingsTitle')}</NavBar>

      <div style={{ margin: '12px 0' }}>
        <List>
          <List.Item
            extra={langLabels[lang] || '中文'}
            onClick={() => setActionSheetVisible(true)}
            arrow
          >
            {t('language')}
          </List.Item>
          <List.Item extra="v0.1.0">
            {t('version')}
          </List.Item>
        </List>
      </div>

      <ActionSheet
        visible={actionSheetVisible}
        actions={languageActions}
        onAction={handleLanguageSelect}
        onClose={() => setActionSheetVisible(false)}
        closeOnAction
      />

      <div style={{ padding: '24px 16px' }}>
        <Button
          block
          color="danger"
          size="large"
          onClick={handleLogout}
        >
          {t('logout')}
        </Button>
      </div>
    </div>
  )
}
