import React, { useEffect, useState } from 'react';
import Sidebar from './Sidebar';
import '../styles/feature.css';
import AddIcon from '../icons/Add.png';
import CalendarIcon from '../icons/Calendar.png';
import ClockIcon from '../icons/Clock.png';
import EditIcon from '../icons/Pencil.png';
import ChatIcon from '../icons/Chat.png';
import ProfileIcon from '../icons/Profile.png';

// New PatientSidebar component
const PatientSidebar = ({ 
  patient = {}, 
  isEditable = false, 
  onSubmit, 
  onClose,
  patientName, 
  setPatientName,
  lastSession, 
  setLastSession,
  nextCheckIn, 
  setNextCheckIn,
  followUpMessage, 
  setFollowUpMessage
}) => {
  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric' 
    });
  };

  const globalClassName = isEditable ? "input-section" : "info-section";

  return (
    <form onSubmit={(e) => {
      e.preventDefault();
      onSubmit();
    }}>
      <div className="card">
        <div className="card-header">
          <h2>{isEditable ? "Check-In Information" : patient.service_user_name}</h2>
          <button className="close-btn" type="button" onClick={onClose}>×</button>
        </div>
        
        {isEditable && (
          <div className="input-section">
            <div className="form-group">
              <label className="section-label" htmlFor="patientName">
                <img src={ProfileIcon} alt="Profile Icon" className="icon" />
                Patient Name
              </label>
              <input 
                type="text" 
                id="patientName" 
                placeholder="Enter service user name"
                value={patientName}
                onChange={(e) => setPatientName(e.target.value)}
              />
            </div>
          </div>
        )}

        <div className={globalClassName}>
          <div className="section-label">
            <img src={CalendarIcon} alt="Calendar Icon" className="icon" />
            Last session
          </div>
          {isEditable ? (
            <input 
              type="date" 
              id="lastSession"
              value={lastSession}
              onChange={(e) => setLastSession(e.target.value)}
            />
          ) : (
            <div className="section-content">{formatDate(patient.last_session)}</div>
          )}
        </div>
        
        <div className={globalClassName}>
          <div className="header-with-actions">
            <div className="section-label">
              <img src={ClockIcon} alt="Clock Icon" className="icon" />
              Recommended check-in
            </div>
            <button className="edit-button" type="button">
              <img src={EditIcon} alt="Edit Icon" className="icon" />
              Edit
            </button>
          </div>
          {isEditable ? (
            <input 
              type="date" 
              id="nextCheckIn"
              value={nextCheckIn}
              onChange={(e) => setNextCheckIn(e.target.value)}
            />
          ) : (
            <div className="section-content">{formatDate(patient.check_in)}</div>
          )}
        </div>
        
        <div>
          <div className="section-label" style={{marginLeft: "20px", marginTop: "16px"}}>
            <img src={ChatIcon} alt="Chat Icon" className="icon" />
            Recommended follow-up message
          </div>
          
          <div className="message-box">
            {isEditable ? (
              <textarea 
                id="followUpMessage" 
                placeholder="Enter follow-up message"
                value={followUpMessage}
                onChange={(e) => setFollowUpMessage(e.target.value)}
              ></textarea>
            ) : (
              <div>
                <div className="header-with-actions">
                  <div></div>
                  <button className="edit-button" type="button">
                    <img src={EditIcon} alt="Edit Icon" className="icon" />
                    Edit
                  </button>
                </div>
                <div>"{patient.follow_up_message}"</div>
              </div>
            )}
          </div>
        </div>
        
        {isEditable && (
          <div className="save-button-container">
            <button type="submit" className="save-button">Save</button>
          </div>
        )}
      </div>
    </form>
  );
};

const ProfileManager = () => {
  const [allNames, setAllNames] = useState([{}]);
  const [hasSidebar, setSidebar] = useState(false);
  const [search, setSearch] = useState('');
  
  // Form state
  const [currentPatient, setCurrentPatient] = useState({});
  const [isEditable, setIsEditable] = useState(false);
  const [patientName, setPatientName] = useState('');
  const [lastSession, setLastSession] = useState('');
  const [nextCheckIn, setNextCheckIn] = useState('');
  const [followUpMessage, setFollowUpMessage] = useState('');

  const handleSearchChange = (e) => {
    setSearch(e.target.value);
  };

  const handleSubmit = async () => {
    // Process form data
    console.log();
    
    try {
      const response = await fetch("http://localhost:8000/new_checkin/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          patientName, lastSession, nextCheckIn, followUpMessage }),
      });
  
      const result = await response.json();
      console.log("Response:", result);
    } catch (error) {
      console.error("Error:", error);
    }
  

    // Here you would typically save the data to your backend
    // savePatientData({ patientName, lastSession, nextCheckIn, followUpMessage });
    
    // Close sidebar after submission
    setSidebar(false);
  };

  const openSidebar = (patient, editable) => {
    // Set current patient data
    setCurrentPatient(patient);
    setIsEditable(editable);
    
    // For new patients (editable=true), initialize with empty values
    // For existing patients (editable=false), initialize with their current values
    if (editable) {
      setPatientName('');
      setLastSession('');
      setNextCheckIn('');
      setFollowUpMessage('');
    } else {
      setPatientName(patient.service_user_name || '');
      setLastSession(patient.last_session || '');
      setNextCheckIn(patient.check_in || '');
      setFollowUpMessage(patient.follow_up_message || '');
    }
    
    // Open the sidebar
    setSidebar(true);
  };

  const getAllNames = async () => {
    const response = await fetch(`http://${window.location.hostname}:8000/service_user_list/?name=naveen`);
    response.json().then((res) => setAllNames(res));
  };

  useEffect(() => {
    getAllNames();
  }, []);

  return (
    <div className="container">
      <div className={`main-content ${hasSidebar ? 'shifted' : ''}`}>
        <div className="search-container"> 
          <input 
            type="text" 
            placeholder="Search Name, Date, etc." 
            className="profile-search-box" 
            value={search}
            onChange={handleSearchChange}
          />
          <button className="add" onClick={() => openSidebar({}, true)}>
            <img src={AddIcon} alt="Add Icon" /> Add
          </button>
        </div>
        
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Location</th>
              <th>Other Info 1</th>
              <th>Other Info 2</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {allNames.map((d, index) => (
              (d.location !== undefined && d.location.toLowerCase().includes(search.toLowerCase())) || 
              (d.service_user_name !== undefined && d.service_user_name.toLowerCase().includes(search.toLowerCase()))
            ) ? (
              <tr key={index} onClick={() => openSidebar(d, false)}>
                <td>{d.service_user_name}</td>
                <td>{d.location}</td>
                <td>Other Info 1</td>
                <td>Other Info 2</td>
                <td><div className={d.status}>{d.status}</div></td>
              </tr>
            ) : null)}      
          </tbody>
        </table>
      </div>
      
      <Sidebar 
      isOpen={hasSidebar}
      content={
        hasSidebar ? (
          <PatientSidebar
            patient={currentPatient}
            isEditable={isEditable}
            onSubmit={handleSubmit}
            onClose={() => setSidebar(false)}
            patientName={patientName}
            setPatientName={setPatientName}
            lastSession={lastSession}
            setLastSession={setLastSession}
            nextCheckIn={nextCheckIn}
            setNextCheckIn={setNextCheckIn}
            followUpMessage={followUpMessage}
            setFollowUpMessage={setFollowUpMessage}
          />
        ) : null
      }
    />

    </div>
  );
};

export default ProfileManager;