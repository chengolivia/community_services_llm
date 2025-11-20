import CalendarIcon from '../icons/Calendar.png';
import ClockIcon from '../icons/Clock.png';
import EditIcon from '../icons/Pencil.png';
import ChatIcon from '../icons/Chat.png';
import ProfileIcon from '../icons/Profile.png';
import React, { useRef, useContext, useEffect, useState } from 'react';


// New PatientSidebar component
const SidebarInformation = ({ 
  patient = {}, 
  checkIns = [],
  isEditable = false,
  isSubmitting = false, 
  onSubmit, 
  onUpdatePatient,
  onSaveAllCheckIns,
  pendingCheckInEdits,
  setPendingCheckInEdits,
  onClose,
  patientName, 
  setPatientName,
  lastSession, 
  setLastSession,
}) => {
  const formatDate = (dateString) => {
    if (!dateString) return '';
    const [year, month, day] = dateString.split('-').map(Number);
    const date = new Date(year, month - 1, day); // month is 0-indexed 
    return date.toLocaleDateString('en-US', {
      year: 'numeric', 
      month: 'short', 
      day: 'numeric' 
    });
  };

  const globalClassName = isEditable ? "input-section" : "info-section";

  const [editedData, setEditedData] = useState({
    patientName: patient.service_user_name || '',
    lastSession: formatDate(patient.last_session),
  });

  
  useEffect(() => {
    setEditedData({
      patientName: patient.service_user_name || '',
      lastSession: formatDate(patient.last_session),
    });
  }, [patient]);

  const handleCheckInEdit = (checkInId, updatedData) => {
    setPendingCheckInEdits(prev => ({
      ...prev,
      [checkInId]: updatedData
    }));
  };

  const handleSaveAll = async () => {
    // Save patient data
    if (onUpdatePatient && lastSession) {
      await onUpdatePatient({
        last_session: lastSession
      });
    }
    
    // Save all modified check-ins
    if (onSaveAllCheckIns && Object.keys(pendingCheckInEdits).length > 0) {
      await onSaveAllCheckIns(pendingCheckInEdits);
    }
  };


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
          {(
            <input 
              type="date" 
              id="lastSession"
              value={lastSession || " "}
              onChange={(e) => setLastSession(e.target.value)}
            />
          )}
        </div>
        
        
       
        {/* Replace single check-in with multiple check-ins */}
        {checkIns.length > 0 && (
          <div>
            <div className="section-label" style={{marginLeft: "20px", marginTop: "16px"}}>
              <img src={ClockIcon} alt="Clock Icon" className="icon" />
              Upcoming Check-ins
            </div>
            {checkIns.map((checkIn, index) => (
              <CheckInItem 
                key={checkIn.id || index} 
                checkIn={checkIn}
                onEdit={handleCheckInEdit}
                formatDate={formatDate}
              />
            ))}
          </div>
        )}
        
        {(<div className="save-button-container">
            <button 
              onClick={handleSaveAll} 
              disabled={isSubmitting}
              type="button" 
              className="save-button"
            >
              {isSubmitting ? 'Saving...' : 'Save Changes'}
            </button>
          </div>)
          }
      </div>
    </form>
  );
};

const CheckInItem = ({checkIn, onEdit}) => {
  const formatDateForInput = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const dd = String(date.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  };

  const [editedCheckIn, setEditedCheckIn] = useState({
    checkInDate: formatDateForInput(checkIn.check_in),
    message: checkIn.follow_up_message
  });

  const handleChange = (field, value) => {
    const updated = {
      ...editedCheckIn,
      [field]: value
    };
    setEditedCheckIn(updated);
    
    // Notify parent component
    onEdit(checkIn.id, {
      check_in: field === 'checkInDate' ? value : editedCheckIn.checkInDate,
      follow_up_message: field === 'message' ? value : editedCheckIn.message
    });
  };
  return (
    <div className="check-in-item" style={{
      margin: "10px 20px",
      padding: "10px",
      border: "1px solid #e0e0e0",
      borderRadius: "8px",
      backgroundColor: "#f9f9f9"
    }}>
      <div style={{ fontWeight: "bold", marginBottom: "5px", display: "flex", alignItems: "center" }}>
        <img src={ClockIcon} alt="Clock Icon" className="icon" style={{width: "16px", marginRight: "5px"}} />
        <input 
          type="date"
          value={editedCheckIn.checkInDate}
          onChange={(e) => setEditedCheckIn(prev => ({
            ...prev,
            checkInDate: e.target.value
          }))}
          style={{ border: "1px solid #ccc", padding: "5px", borderRadius: "4px" }}
        />
      </div>
      
      {/* Remove the message-box wrapper and use a plain div */}
      <div style={{marginTop: "10px"}}>
        <div style={{display: "flex", alignItems: "center", marginBottom: "5px"}}>
          <img src={ChatIcon} alt="Chat Icon" className="icon" style={{width: "16px", marginRight: "5px"}} />
          <span style={{fontSize: "14px", color: "#666"}}>Follow-up message</span>
        </div>
        <textarea
          value={editedCheckIn.message}
          onChange={(e) => handleChange('message', e.target.value)}
          style={{ 
            width: "100%", 
            minHeight: "60px",
            border: "1px solid #ccc", 
            padding: "8px", 
            borderRadius: "4px",
            resize: "vertical",
            fontFamily: "inherit",
            fontSize: "14px",
            boxSizing: "border-box"
          }}
        />
      </div>
    </div>
  );
};

export default SidebarInformation;
