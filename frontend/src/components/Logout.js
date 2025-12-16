// Logout.js - Clears auth and redirects to login
import React, { useContext } from 'react';
import { WellnessContext } from './AppStateContextProvider';
import { useNavigate } from 'react-router-dom';

/**
 * Logout component - clears local state/localStorage and navigates to login
 */

function Logout() {
  const { setUser, setOrganization, setConversation } = useContext(WellnessContext);
  const navigate = useNavigate();

  const handleLogout = () => {
    setUser({
      username: '',
      role: '',
      isAuthenticated: false,
      token: null,
    });
    setOrganization('');
    setConversation([]);
    
    localStorage.removeItem('accessToken');
    localStorage.removeItem('userRole');
    localStorage.removeItem('username');
    
    navigate('/login');
  };

  return (
    <button onClick={handleLogout} className="logout-button">
      Logout
    </button>
  );
}

export default Logout;