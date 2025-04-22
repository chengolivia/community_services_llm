import React, { useState, useContext } from 'react';
import { Link, useLocation } from 'react-router-dom';
import '../App.css';
import HomeIcon from '../icons/Home.png';
import WellnessGoalsIcon from '../icons/WellnessGoalsAssistant.png';
import { WellnessContext } from './AppStateContextProvider';

function Navbar() {
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const { organization } = useContext(WellnessContext);
  
  const toggleMenu = () => {
    setMenuOpen(!menuOpen);
  };
  
  // Convert organization to uppercase for display
  const displayOrganization = organization ? organization.toUpperCase() : '';
  
  return (
    <nav className="navbar">
      <h1 className="navbar-title">PeerCoPilot</h1>
      <h3 className="navbar-subtitle">{displayOrganization}</h3>
      <div className="hamburger" onClick={toggleMenu}>
        &#9776; {/* Hamburger icon */}
      </div>
      <div className={`navbar-links ${menuOpen ? 'active' : ''}`}>
        <Link
          to="/"
          className={`navbar-button ${location.pathname === '/' ? 'active' : ''}`}
        >
          <img src={HomeIcon} alt="Home Icon" className="navbar-icon" />
          Home
        </Link>
        <div className="navbar-spacer"></div>
        <div className="navbar-label">Tool</div>
        <Link
          to="/wellness-goals"
          className={`navbar-button ${
            location.pathname === '/wellness-goals' ? 'active' : ''
          }`}
        >
          <img src={WellnessGoalsIcon} alt="Wellness Goals Icon" className="navbar-icon" />
          Wellness Planner
        </Link>
      </div>
    </nav>
  );
}

export default Navbar;