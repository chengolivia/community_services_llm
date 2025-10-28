import React, { useState, useContext } from 'react';
import { WellnessContext } from './AppStateContextProvider';
import { useNavigate } from 'react-router-dom';


function Logout() {
  const { setUser, setOrganization } = useContext(WellnessContext);
  const navigate = useNavigate();

  const handleLogout = () => {
    setUser({
      username: '',
      role: '',
      isAuthenticated: false, 
    });
    setOrganization(''); // Don't forget this!
    navigate('/login');
  };
  return (
    <button onClick={handleLogout} className="logout-button">
      Logout
    </button>
  );

}

export default Logout;