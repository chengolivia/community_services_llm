import CalendarIcon from '../icons/Calendar.png';
import ClockIcon from '../icons/Clock.png';
import EditIcon from '../icons/Pencil.png';
import ChatIcon from '../icons/Chat.png';
import ProfileIcon from '../icons/Profile.png';

// Updated SidebarInformation component
const SidebarInformation = ({ 
  patient = {}, 
  isEditable = false,
  isSubmitting = false, 
  formData = {},
  onFormChange,
  onSubmit, 
  onClose,
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
                value={formData.patientName || ''}
                onChange={(e) => onFormChange('patientName', e.target.value)}
              />
            </div>
          </div>
        )}
        {isEditable && (
          <div className="input-section">
            <div className="form-group">
              <label className="section-label" htmlFor="location">
                <img src={ProfileIcon} alt="Location Icon" className="icon" />
                Location
              </label>
              <input 
                type="text" 
                id="location" 
                placeholder="Enter location (e.g., city, clinic name)"
                value={formData.location || ''}
                onChange={(e) => onFormChange('location', e.target.value)}
              />
            </div>
          </div>
        )}

        {!isEditable && patient.location && (
          <div className="info-section">
            <div className="section-label">
              <img src={ProfileIcon} alt="Location Icon" className="icon" />
              Location
            </div>
            <div className="section-content">{patient.location}</div>
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
              value={formData.lastSession || ''}
              onChange={(e) => onFormChange('lastSession', e.target.value)}
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
              value={formData.nextCheckIn || ''}
              onChange={(e) => onFormChange('nextCheckIn', e.target.value)}
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
                value={formData.followUpMessage || ''}
                onChange={(e) => onFormChange('followUpMessage', e.target.value)}
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
            <button 
              onClick={onSubmit} 
              disabled={isSubmitting || !formData.patientName} 
              type="submit" 
              className="save-button"
            >
              {isSubmitting ? 'Saving...' : 'Save Check-in'}
            </button>
          </div>
        )}
      </div>
    </form>
  );
};

export default SidebarInformation;
