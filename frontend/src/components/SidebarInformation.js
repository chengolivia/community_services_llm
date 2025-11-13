import CalendarIcon from '../icons/Calendar.png';
import ClockIcon from '../icons/Clock.png';
import EditIcon from '../icons/Pencil.png';
import ChatIcon from '../icons/Chat.png';
import ProfileIcon from '../icons/Profile.png';

// New PatientSidebar component
const SidebarInformation = ({ 
  patient = {}, 
  checkIns = [],
  isEditable = false,
  isSubmitting = false, 
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
    const [year, month, day] = dateString.split('-').map(Number);
    const date = new Date(year, month - 1, day); // month is 0-indexed 
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
        
        {/* <div className={globalClassName}>
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
        </div> */}

        {/* Replace single check-in with multiple check-ins */}
        {!isEditable && checkIns.length > 0 ? (
          <div>
            <div className="section-label" style={{marginLeft: "20px", marginTop: "16px"}}>
              <img src={ClockIcon} alt="Clock Icon" className="icon" />
              Upcoming Check-ins
            </div>
            {checkIns.map((checkIn, index) => (
              <div key={checkIn.id || index} className="check-in-item" style={{
                margin: "10px 20px",
                padding: "10px",
                border: "1px solid #e0e0e0",
                borderRadius: "8px",
                backgroundColor: "#f9f9f9"
              }}>
                <div style={{ fontWeight: "bold", marginBottom: "5px" }}>
                  <img src={ClockIcon} alt="Clock Icon" className="icon" style={{width: "16px", marginRight: "5px"}} />
                  {formatDate(checkIn.check_in)}
                </div>
                <div className="message-box" style={{marginTop: "5px"}}>
                  <img src={ChatIcon} alt="Chat Icon" className="icon" style={{width: "16px", marginRight: "5px"}} />
                  {checkIn.follow_up_message}
                </div>
              </div>
            ))}
          </div>
        ) : isEditable ? (
          // Keep original editable fields for backward compatibility
          <>
            {/* <div className={globalClassName}>
              <div className="header-with-actions">
                <div className="section-label">
                  <img src={ClockIcon} alt="Clock Icon" className="icon" />
                  Recommended check-in
                </div>
              </div>
              <input 
                type="date" 
                id="nextCheckIn"
                value={nextCheckIn}
                onChange={(e) => setNextCheckIn(e.target.value)}
              />
            </div>
            
            <div>
              <div className="section-label" style={{marginLeft: "20px", marginTop: "16px"}}>
                <img src={ChatIcon} alt="Chat Icon" className="icon" />
                Recommended follow-up message
              </div>
              
              <div className="message-box">
                <textarea 
                  id="followUpMessage" 
                  placeholder="Enter follow-up message"
                  value={followUpMessage}
                  onChange={(e) => setFollowUpMessage(e.target.value)}
                ></textarea>
              </div>
            </div> */}
          </>
        ) : null}
        
        {isEditable && (
          <div className="save-button-container">
            <button onClick={onSubmit} disabled={isSubmitting || !patientName} type="submit" className="save-button">{isSubmitting ? 'Saving...' : 'Save Check-in'}</button>
          </div>
        )}
      </div>
    </form>
  );
};

export default SidebarInformation;
