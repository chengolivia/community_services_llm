import React, { useContext, useEffect } from 'react';
import { Link } from 'react-router-dom';
import '../App.css';
import Logo from '../icons/Logo.png';
import {WellnessContext } from './AppStateContextProvider';

function Home() {
  const { organization, setOrganization } = useContext(WellnessContext);

  const handleOrganizationChange = (e) => {
    const newOrg = e.target.value.toLowerCase();
    console.log("Setting organization to:", newOrg); // For debugging
    setOrganization(newOrg);
  };

  // For debugging - verify the context is working
  useEffect(() => {
    console.log("Current organization:", organization);
  }, [organization]);

  return (
    <div className="home-container">
      <div className="home-logo">
        <img src={Logo} alt="Logo" />
      </div>
      
      <h1 className="home-heading">Welcome!</h1>
      <p className="home-subheading">All Tools at One Glance:</p>
      <div className="tiles-container">
        <Link to="/wellness-goals" className="tile">
          <span>Tool 1</span>
          <h2>Wellness Planner</h2>
        </Link>
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
    </div>
  );
}

export default Home;