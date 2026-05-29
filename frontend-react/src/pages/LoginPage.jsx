import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { NavBar, Button, Form, Input, Toast } from 'antd-mobile';
import { login, register, updateAuthHeader } from '../api';
import useUserStore from '../stores/userStore';

const LoginPage = () => {
  const navigate = useNavigate();
  const { setToken } = useUserStore();

  const [tabActive, setTabActive] = useState('login');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [nickname, setNickname] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!phone || !password) {
      Toast.show('请填写手机号和密码');
      return;
    }
    setLoading(true);
    try {
      const res = await login({ phone, password });
      const token = res.data?.token || res.token;
      updateAuthHeader(token);
      setToken(token);
      Toast.show('登录成功');
      navigate('/profile');
    } catch (err) {
      Toast.show(err?.response?.data?.message || '登录失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async () => {
    if (!phone || !password || !nickname) {
      Toast.show('请填写所有必填字段');
      return;
    }
    if (password !== confirmPassword) {
      Toast.show('两次输入的密码不一致');
      return;
    }
    setLoading(true);
    try {
      const res = await register({ phone, password, nickname });
      const token = res.data?.token || res.token;
      updateAuthHeader(token);
      setToken(token);
      Toast.show('注册成功');
      navigate('/profile');
    } catch (err) {
      Toast.show(err?.response?.data?.message || '注册失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const switchTab = (key) => {
    setTabActive(key);
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
      <NavBar onBack={() => navigate(-1)}>登录</NavBar>

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
          登录
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
          注册
        </div>
      </div>

      {/* Login Form */}
      {tabActive === 'login' && (
        <div style={{ padding: '24px 16px' }}>
          <Form>
            <Form.Item label="手机号">
              <Input
                placeholder="请输入手机号"
                value={phone}
                onChange={(val) => setPhone(val)}
                type="tel"
                clearable
              />
            </Form.Item>
            <Form.Item label="密码">
              <Input
                placeholder="请输入密码"
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
                登录
              </Button>
            </div>
          </Form>
        </div>
      )}

      {/* Register Form */}
      {tabActive === 'register' && (
        <div style={{ padding: '24px 16px' }}>
          <Form>
            <Form.Item label="手机号">
              <Input
                placeholder="请输入手机号"
                value={phone}
                onChange={(val) => setPhone(val)}
                type="tel"
                clearable
              />
            </Form.Item>
            <Form.Item label="昵称">
              <Input
                placeholder="请输入昵称"
                value={nickname}
                onChange={(val) => setNickname(val)}
                clearable
              />
            </Form.Item>
            <Form.Item label="密码">
              <Input
                placeholder="请输入密码"
                value={password}
                onChange={(val) => setPassword(val)}
                type="password"
                clearable
              />
            </Form.Item>
            <Form.Item label="确认密码">
              <Input
                placeholder="请再次输入密码"
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
                注册
              </Button>
            </div>
          </Form>
        </div>
      )}
    </div>
  );
};

export default LoginPage;
