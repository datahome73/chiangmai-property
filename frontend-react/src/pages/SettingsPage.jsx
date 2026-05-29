import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { NavBar, List, Button, ActionSheet } from 'antd-mobile';
import { clearAuthHeader } from '../api';
import useUserStore from '../stores/userStore';

const languageLabels = {
  zh: '中文',
  en: 'English',
  th: 'ภาษาไทย',
};

const languageActions = [
  { key: 'zh', text: '中文' },
  { key: 'en', text: 'English' },
  { key: 'th', text: 'ภาษาไทย' },
];

const SettingsPage = () => {
  const navigate = useNavigate();
  const { logout } = useUserStore();

  const [language, setLanguage] = useState('zh');
  const [actionSheetVisible, setActionSheetVisible] = useState(false);

  const handleLanguageSelect = (item) => {
    setLanguage(item.key);
    setActionSheetVisible(false);
  };

  const handleLogout = () => {
    ActionSheet.show({
      actions: [{ key: 'confirm', text: '确认退出', danger: true }],
      onAction: (item) => {
        if (item.key === 'confirm') {
          clearAuthHeader();
          logout();
          navigate('/profile');
        }
      },
      onClose: () => {},
    });
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
      <NavBar onBack={() => navigate(-1)}>设置</NavBar>

      <div style={{ margin: '12px 0' }}>
        <List>
          <List.Item
            extra={languageLabels[language] || '中文'}
            onClick={() => setActionSheetVisible(true)}
            arrow
          >
            语言
          </List.Item>
          <List.Item extra="v0.1.0">
            版本号
          </List.Item>
        </List>
      </div>

      {/* Language ActionSheet */}
      <ActionSheet
        visible={actionSheetVisible}
        actions={languageActions}
        onAction={handleLanguageSelect}
        onClose={() => setActionSheetVisible(false)}
        closeOnAction
      />

      {/* Logout button */}
      <div style={{ padding: '24px 16px' }}>
        <Button
          block
          color="danger"
          size="large"
          onClick={handleLogout}
        >
          退出登录
        </Button>
      </div>
    </div>
  );
};

export default SettingsPage;
