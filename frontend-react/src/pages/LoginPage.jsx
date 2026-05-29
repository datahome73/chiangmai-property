import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { NavBar, Button, Form, Input, Toast } from 'antd-mobile';
import { login, register, updateAuthHeader } from '../api';
import useUserStore from '../stores/userStore';
import { useT } from '../i18n';

const LoginPage = () => {
  const navigate = useNavigate();
  const { setToken } = useUserStore();
  const t = useT();

  const [tabActive, setTabActive] = useState('login');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [nickname, setNickname] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!phone || !password) {
      Toast.show(t('fillRequired'));
      return;
    }
    setLoading(true);
    try {
      const res = await login({ phone, password });
      const token = res.data?.token || res.token;
      updateAuthHeader(token);
      setToken(token);
      Toast.show(t('loginSuccess'));
      navigate('/profile');
    } catch (err) {
      Toast.show(err?.response?.data?.message || t('loginFailed'));
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async () => {
    if (!phone || !password || !nickname) {
      Toast.show(t('fillRequired'));
      return;
    }
    if (password !== confirmPassword) {
      Toast.show(t('passwordMismatch'));
      return;
    }
    setLoading(true);
    try {
      const res = await register({ phone, password, nickname });
      const token = res.data?.token || res.token;
      updateAuthHeader(token);
      setToken(token);
      Toast.show(t('registerSuccess'));
      navigate('/profile');
    } catch (err) {
      Toast.show(err?.response?.data?.message || t('registerFailed'));
    } finally {
      setLoading(false);
    }
  };

  const switchTab = (key) => {
    setTabActive(key);
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
      <NavBar onBack={() => navigate(-1)}>{t('login')}</NavBar>

      {/* Tabs */}
      <div
        style={{
          display: 'flex',
          borderBottom: '1px solid #eee',
          backgroundColor: '#fff',
        }}
      >
        <div
          style={{
            flex: 1,
            textAlign: 'center',
            padding: '14px 0',
            fontWeight: tabActive === 'login' ? 600 : 400,
            color: tabActive === 'login' ? '#1677ff' : '#666',
            borderBottom: tabActive === 'login' ? '2px solid #1677ff' : '2px solid transparent',
            cursor: 'pointer',
          }}
          onClick={() => switchTab('login')}
        >
          {t('login')}
        </div>
        <div
          style={{
            flex: 1,
            textAlign: 'center',
            padding: '14px 0',
            fontWeight: tabActive === 'register' ? 600 : 400,
            color: tabActive === 'register' ? '#1677ff' : '#666',
            borderBottom: tabActive === 'register' ? '2px solid #1677ff' : '2px solid transparent',
            cursor: 'pointer',
          }}
          onClick={() => switchTab('register')}
        >
          {t('register')}
        </div>
      </div>

      {/* Login Form */}
      {tabActive === 'login' && (
        <div style={{ padding: '24px 16px' }}>
          <Form>
            <Form.Item label={t('phoneNumber')}>
              <Input
                placeholder={t('enterPhone')}
                value={phone}
                onChange={(val) => setPhone(val)}
                type="tel"
                clearable
              />
            </Form.Item>
            <Form.Item label={t('password')}>
              <Input
                placeholder={t('enterPassword')}
                value={password}
                onChange={(val) => setPassword(val)}
                type="password"
                clearable
              />
            </Form.Item>
            <div style={{ marginTop: 32 }}>
              <Button
                block
                color="primary"
                size="large"
                loading={loading}
                onClick={handleLogin}
              >
                {t('login')}
              </Button>
            </div>
          </Form>
        </div>
      )}

      {/* Register Form */}
      {tabActive === 'register' && (
        <div style={{ padding: '24px 16px' }}>
          <Form>
            <Form.Item label={t('phoneNumber')}>
              <Input
                placeholder={t('enterPhone')}
                value={phone}
                onChange={(val) => setPhone(val)}
                type="tel"
                clearable
              />
            </Form.Item>
            <Form.Item label={t('nickname')}>
              <Input
                placeholder={t('enterNickname')}
                value={nickname}
                onChange={(val) => setNickname(val)}
                clearable
              />
            </Form.Item>
            <Form.Item label={t('password')}>
              <Input
                placeholder={t('enterPassword')}
                value={password}
                onChange={(val) => setPassword(val)}
                type="password"
                clearable
              />
            </Form.Item>
            <Form.Item label={t('confirmPassword')}>
              <Input
                placeholder={t('reenterPassword')}
                value={confirmPassword}
                onChange={(val) => setConfirmPassword(val)}
                type="password"
                clearable
              />
            </Form.Item>
            <div style={{ marginTop: 32 }}>
              <Button
                block
                color="primary"
                size="large"
                loading={loading}
                onClick={handleRegister}
              >
                {t('register')}
              </Button>
            </div>
          </Form>
        </div>
      )}
    </div>
  );
};

export default LoginPage;
