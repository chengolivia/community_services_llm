import React, { useContext, useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import Logo from '../icons/Logo.png';
import {WellnessContext } from './AppStateContextProvider';
import { authenticatedFetch } from '../utils/api';

import { API_URL } from '../config';

import '../styles/pages/home.css';


function Home() {
  const { organization, setOrganization, user } = useContext(WellnessContext);
  const [showSettings, setShowSettings] = useState(false);
  const [email, setEmail] = useState('');
  const [notificationsEnabled, setNotificationsEnabled] = useState(false);
  const [notificationTime, setNotificationTime] = useState('08:00');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const handleOrganizationChange = (e) => {
    const newOrg = e.target.value.toLowerCase();
    console.log("Setting organization to:", newOrg); // For debugging
    setOrganization(newOrg);
  };

  useEffect(() => {
    console.log("Current organization:", organization);
  }, [organization]);

  useEffect(() => {
    if (showSettings) {
      fetchSettings();
    }
  }, [showSettings]);

  const fetchSettings = async () => {
    const token = user.token || localStorage.getItem('accessToken');
    
    if (!token) {
      setMessage('Not authenticated. Please log in again.');
      return;
    }
    try {
      const response = await authenticatedFetch(`/api/notification-settings`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });
          const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
      console.error('Expected JSON but got:', contentType);
      console.error('Response status:', response.status);
      return;
    }
      const data = await response.json();
      if (data.success) {
        setEmail(data.settings.email || '');
        setNotificationsEnabled(data.settings.notifications_enabled || false);
        setNotificationTime(data.settings.notification_time || '08:00');
      }
    } catch (error) {
      console.error('Error fetching settings:', error);
    }
  };

  const handleSaveSettings = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');
    const token = user.token || localStorage.getItem('accessToken');
    
    if (!token) {
      setMessage('Not authenticated. Please log in again.');
      return;
    }

    try {
      const response = await authenticatedFetch(`/api/notification-settings`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          username: user.username,
          email,
          notifications_enabled: notificationsEnabled,
          notification_time: notificationTime
        })
      });

      const data = await response.json();
      if (data.success) {
        setMessage('Settings saved successfully!');
        setTimeout(() => setMessage(''), 3000);
      } else {
        setMessage(`Error: ${data.message}`);
      }
    } catch (error) {
      setMessage('Error saving settings');
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };
    
  // Redirect to login if not authenticated
  if (user.username === '' || !user.isAuthenticated) {
    return <Navigate to="/login" />;
  }

  return (
    <div className="home-container">
      <div className="home-logo">
        <img src={Logo} alt="Logo" />
      </div>
      
      <h1 className="home-heading">Welcome, {user.username}!</h1>
      <p className="home-subheading">All Tools at One Glance:</p>
      <div className="tools">  
        <div className="tiles-container">
          <Link to="/wellness-goals" className="tile">
            <span>Tool 1</span>
            <h2>Wellness Planner</h2>
          </Link>
        </div>
        <div className="tiles-container">
          <Link to="/profile-manager" className="tile">
            <span>Tool 2</span>
            <h2>Profile Manager</h2>
          </Link>
        </div>
        <div className="tiles-container">
          <Link to="/outreach-calendar" className="tile">
            <span>Tool 3</span>
            <h2>Outreach Calendar</h2>
          </Link>
        </div>
      </div>
      <div className="organization-selector">
        <label htmlFor="organization-dropdown">Organization: </label>
        <select 
          id="organization-dropdown"
          value={organization === 'cspnj' ? 'cspnj' : 'clhs'}
          onChange={handleOrganizationChange}
          className="organization-dropdown"
        >
          <option value="cspnj">CSPNJ</option>
          <option value="clhs">CLHS</option>
        </select>
      </div>
      <button 
        className="settings-toggle-button"
        onClick={() => setShowSettings(!showSettings)}
      >
        {showSettings ? 'Hide Settings' : 'Notification Settings'}
      </button>
      {showSettings && (
        <div className="notification-settings-panel">
          <h3>Notification Settings</h3>
          <form onSubmit={handleSaveSettings} className="settings-form">
            <div className="form-group">
              <label htmlFor="email">Email Address:</label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your.email@example.com"
                required
              />
            </div>

            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  checked={notificationsEnabled}
                  onChange={(e) => setNotificationsEnabled(e.target.checked)}
                />
                Enable email notifications for check-ins
              </label>
            </div>

            {notificationsEnabled && (
              <div className="form-group">
                <label htmlFor="notification-time">Daily notification time:</label>
                <input
                  type="time"
                  id="notification-time"
                  value={notificationTime}
                  onChange={(e) => setNotificationTime(e.target.value)}
                />
                <small>You'll receive a daily summary of upcoming check-ins at this time</small>
              </div>
            )}

            <button type="submit" disabled={loading} className="settings-toggle-button">
              {loading ? 'Saving...' : 'Save Settings'}
            </button>

            {message && (
              <div className={`message ${message.includes('Error') ? 'error' : 'success'}`}>
                {message}
              </div>
            )}
          </form>
        </div>
      )}
    </div>
  );
}

export default Home;