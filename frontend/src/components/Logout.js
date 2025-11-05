import React, { useContext } from 'react';
import { WellnessContext } from './AppStateContextProvider';
import { useNavigate } from 'react-router-dom';

function Logout() {
  const { setUser, setOrganization } = useContext(WellnessContext);
  const navigate = useNavigate();

  const handleLogout = () => {
    // Clear user state
    setUser({
      username: '',
      role: '',
      isAuthenticated: false,
      token: null, // Clear token
    });
    setOrganization('');
    
    // SECURITY FIX: Clear localStorage
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