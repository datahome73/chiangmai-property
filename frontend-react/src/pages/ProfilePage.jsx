import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, List } from 'antd-mobile';
import usePropertyStore from '../stores/propertyStore';
import useUserStore from '../stores/userStore';
import { useT } from '../i18n';

const ProfilePage = () => {
  const navigate = useNavigate();
  const { user, loading, isLoggedIn, fetchProfile } = useUserStore();
  const { favorites, loadFavorites } = usePropertyStore();
  const t = useT();

  useEffect(() => {
    if (isLoggedIn()) {
      fetchProfile();
      loadFavorites();
    }
  }, []);

  // Not logged in state
  if (!isLoggedIn()) {
    return (
      <div
        style={{
          minHeight: '100vh',
          backgroundColor: '#f5f5f5',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '0 32px',
        }}
      >
        <div
          style={{
            backgroundColor: '#fff',
            borderRadius: 16,
            padding: '48px 40px',
            textAlign: 'center',
            width: '100%',
            maxWidth: 320,
            boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
          }}
        >
          <div
            style={{
              width: 72,
              height: 72,
              borderRadius: '50%',
              backgroundColor: '#e8e8e8',
              margin: '0 auto 16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 32,
              color: '#999',
            }}
          >
            👤
          </div>
          <h3 style={{ margin: '0 0 8px', color: '#333', fontSize: 18 }}>
            {t('welcome')}
          </h3>
          <p style={{ margin: '0 0 24px', color: '#999', fontSize: 14 }}>
            {t('loginPrompt')}
          </p>
          <Button
            block
            color="primary"
            size="large"
            onClick={() => navigate('/login')}
          >
            {t('loginRegister')}
          </Button>
        </div>
      </div>
    );
  }

  // Logged in state
  const avatarChar = user?.nickname
    ? user.nickname.charAt(0).toUpperCase()
    : user?.phone
    ? user.phone.charAt(0)
    : '?';

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
      {/* Top gradient area */}
      <div
        style={{
          background: 'linear-gradient(135deg, #1677ff, #69b1ff)',
          padding: '48px 24px 32px',
          color: '#fff',
          textAlign: 'center',
        }}
      >
        <div
          style={{
            width: 72,
            height: 72,
            borderRadius: '50%',
            backgroundColor: 'rgba(255,255,255,0.25)',
            margin: '0 auto 12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 32,
            fontWeight: 700,
            color: '#fff',
          }}
        >
          {avatarChar}
        </div>
        <div style={{ fontSize: 20, fontWeight: 600, marginBottom: 4 }}>
          {user?.nickname || '用户'}
        </div>
        <div style={{ fontSize: 14, opacity: 0.85 }}>
          {user?.phone || ''}
        </div>
      </div>

      {/* Stats cards */}
      <div
        style={{
          display: 'flex',
          margin: '-16px 16px 0',
          gap: 12,
        }}
      >
        <div
          style={{
            flex: 1,
            backgroundColor: '#fff',
            borderRadius: 12,
            padding: '16px',
            textAlign: 'center',
            boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
          }}
        >
          <div style={{ fontSize: 24, fontWeight: 700, color: '#1677ff' }}>
            {favorites?.length || 0}
          </div>
          <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
            {t('myFavoritesCount')}
          </div>
        </div>
        <div
          style={{
            flex: 1,
            backgroundColor: '#fff',
            borderRadius: 12,
            padding: '16px',
            textAlign: 'center',
            boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
          }}
        >
          <div style={{ fontSize: 24, fontWeight: 700, color: '#1677ff' }}>
            {user?.compareCount || 0}
          </div>
          <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
            {t('myCompare')}
          </div>
        </div>
      </div>

      {/* Menu list */}
      <div style={{ margin: '20px 16px 0' }}>
        <List>
          <List.Item
            onClick={() => navigate('/favorites')}
            arrow
          >
            {t('myFavorites')}
          </List.Item>
          <List.Item
            onClick={() => navigate('/compare')}
            arrow
          >
            {t('myCompare')}
          </List.Item>
          <List.Item
            onClick={() => navigate('/settings')}
            arrow
          >
            {t('settings')}
          </List.Item>
        </List>
      </div>
    </div>
  );
};

export default ProfilePage;
