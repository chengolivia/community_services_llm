// SidebarInformation.js
import CalendarIcon from '../icons/Calendar.png';
import ClockIcon from '../icons/Clock.png';
import EditIcon from '../icons/Pencil.png';
import ChatIcon from '../icons/Chat.png';
import ProfileIcon from '../icons/Profile.png';
import React, { useEffect, useState } from 'react';

// Capitalized so CSS status class highlighting works correctly
const STATUS_OPTIONS = ['Active', 'Inactive', 'Pending', 'Closed'];

const SidebarInformation = ({
  patient = {},
  checkIns = [],
  isEditable = false,
  isSubmitting = false,
  formData = {},
  onFormChange,
  onSubmit,
  onUpdatePatient,
  onSaveAllCheckIns,
  onClose,
}) => {
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [profileEdits, setProfileEdits] = useState({});
  const [pendingCheckInEdits, setPendingCheckInEdits] = useState({});
  const [newCheckIns, setNewCheckIns] = useState([]);

  const formatDateForInput = (dateString) => {
    if (!dateString) return '';
    if (/^\d{4}-\d{2}-\d{2}$/.test(dateString)) return dateString;
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return '';
    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const dd = String(date.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  };

  useEffect(() => {
    setIsEditingProfile(false);
    setProfileEdits({});
    setPendingCheckInEdits({});
    setNewCheckIns([]);
  }, [patient?.service_user_id]);

  // --- Profile edit handlers ---
  const handleStartEditProfile = () => {
    setProfileEdits({
      service_user_name: patient.service_user_name || '',
      location: patient.location || '',
      status: patient.status || '',
      last_session: formatDateForInput(patient.last_session),
    });
    setIsEditingProfile(true);
  };

  const handleProfileFieldChange = (field, value) =>
    setProfileEdits(prev => ({ ...prev, [field]: value }));

  const handleSaveProfile = async () => {
    if (onUpdatePatient) await onUpdatePatient(profileEdits);
    setIsEditingProfile(false);
  };

  // --- Check-in edit handlers ---
  const handleCheckInEdit = (checkInId, updatedData) =>
    setPendingCheckInEdits(prev => ({ ...prev, [checkInId]: updatedData }));

  // --- New check-in handlers ---
  const handleAddNewCheckIn = () =>
    setNewCheckIns(prev => [...prev, { checkInDate: '', message: '' }]);

  const handleNewCheckInChange = (index, field, value) =>
    setNewCheckIns(prev => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });

  const handleRemoveNewCheckIn = (index) =>
    setNewCheckIns(prev => prev.filter((_, i) => i !== index));

  // --- Save all check-in changes ---
  const handleSaveAll = async () => {
    if (isEditable) {
      await onSubmit();
      return;
    }
    const hasEdits = Object.keys(pendingCheckInEdits).length > 0;
    const hasNewCheckIns = newCheckIns.some(ci => ci.checkInDate);

    if (!hasEdits && !hasNewCheckIns) {
      alert('No check-in changes to save');
      return;
    }

    if (onSaveAllCheckIns) {
      // No deletions from sidebar — completion is done from the calendar
      await onSaveAllCheckIns(
        pendingCheckInEdits,
        [],
        newCheckIns.filter(ci => ci.checkInDate)
      );
    }

    setPendingCheckInEdits({});
    setNewCheckIns([]);
  };

  return (
    <form onSubmit={(e) => { e.preventDefault(); onSubmit?.(); }}>
      <div className="card">
        <div className="card-header">
          <h2>
            {isEditable ? 'New Member' : (isEditingProfile ? 'Edit Member' : patient.service_user_name)}
          </h2>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            {!isEditable && !isEditingProfile && (
              <button
                type="button"
                onClick={handleStartEditProfile}
                title="Edit profile"
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}
              >
                <img src={EditIcon} alt="Edit" style={{ width: '18px' }} />
              </button>
            )}
            <button className="close-btn" type="button" onClick={onClose}>×</button>
          </div>
        </div>

        {/* ── NEW PATIENT FORM ── */}
        {isEditable && (
          <>
            <div className="input-section">
              <div className="form-group">
                <label className="section-label" htmlFor="patientName">
                  <img src={ProfileIcon} alt="" className="icon" /> Member Name
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

            <div className="input-section">
              <div className="form-group">
                <label className="section-label" htmlFor="location">
                  <img src={ProfileIcon} alt="" className="icon" /> Location
                </label>
                <input
                  type="text"
                  id="location"
                  placeholder="Enter location"
                  value={formData.location || ''}
                  onChange={(e) => onFormChange('location', e.target.value)}
                />
              </div>
            </div>

            <div className="input-section">
              <div className="form-group">
                <label className="section-label" htmlFor="lastSession">
                  <img src={CalendarIcon} alt="" className="icon" /> Last Session
                </label>
                <input
                  type="date"
                  id="lastSession"
                  value={formData.lastSession || ''}
                  onChange={(e) => onFormChange('lastSession', e.target.value)}
                />
              </div>
            </div>

            <div className="input-section">
              <div className="form-group">
                <label className="section-label" htmlFor="nextCheckIn">
                  <img src={ClockIcon} alt="" className="icon" /> Next Check-in Date
                </label>
                <input
                  type="date"
                  id="nextCheckIn"
                  value={formData.nextCheckIn || ''}
                  onChange={(e) => onFormChange('nextCheckIn', e.target.value)}
                />
              </div>
            </div>

            <div className="input-section">
              <div className="form-group">
                <label className="section-label" htmlFor="followUpMessage">
                  <img src={ChatIcon} alt="" className="icon" /> Follow-up Message
                </label>
                <textarea
                  id="followUpMessage"
                  placeholder="Enter follow-up message"
                  value={formData.followUpMessage || ''}
                  onChange={(e) => onFormChange('followUpMessage', e.target.value)}
                  style={{ width: '100%', minHeight: '60px', padding: '8px', borderRadius: '4px', border: '1px solid #ccc', fontFamily: 'inherit', fontSize: '14px', boxSizing: 'border-box', resize: 'vertical' }}
                />
              </div>
            </div>

            <div className="input-section">
              <div className="form-group">
                <label className="section-label" htmlFor="status">
                  <img src={ProfileIcon} alt="" className="icon" /> Status
                </label>
                <select
                  id="status"
                  value={formData.status || ''}
                  onChange={(e) => onFormChange('status', e.target.value)}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
                >
                  <option value="">Select status...</option>
                  {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
            </div>
          </>
        )}

        {/* ── EDIT EXISTING PROFILE ── */}
        {!isEditable && isEditingProfile && (
          <>
            <div className="input-section">
              <div className="form-group">
                <label className="section-label">
                  <img src={ProfileIcon} alt="" className="icon" /> Member Name
                </label>
                <input
                  type="text"
                  value={profileEdits.service_user_name || ''}
                  onChange={(e) => handleProfileFieldChange('service_user_name', e.target.value)}
                />
              </div>
            </div>

            <div className="input-section">
              <div className="form-group">
                <label className="section-label">
                  <img src={ProfileIcon} alt="" className="icon" /> Location
                </label>
                <input
                  type="text"
                  value={profileEdits.location || ''}
                  onChange={(e) => handleProfileFieldChange('location', e.target.value)}
                />
              </div>
            </div>

            <div className="input-section">
              <div className="form-group">
                <label className="section-label">
                  <img src={CalendarIcon} alt="" className="icon" /> Last Session
                </label>
                <input
                  type="date"
                  value={profileEdits.last_session || ''}
                  onChange={(e) => handleProfileFieldChange('last_session', e.target.value)}
                />
              </div>
            </div>

            <div className="input-section">
              <div className="form-group">
                <label className="section-label">
                  <img src={ProfileIcon} alt="" className="icon" /> Status
                </label>
                <select
                  value={profileEdits.status || ''}
                  onChange={(e) => handleProfileFieldChange('status', e.target.value)}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
                >
                  <option value="">Select status...</option>
                  {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px', margin: '0 20px 12px' }}>
              <button
                type="button"
                className="save-button"
                onClick={handleSaveProfile}
                disabled={isSubmitting}
                style={{ flex: 1 }}
              >
                {isSubmitting ? 'Saving...' : 'Save Profile'}
              </button>
              <button
                type="button"
                className="save-button"
                onClick={() => setIsEditingProfile(false)}
                style={{ flex: 1, background: '#aaa' }}
              >
                Cancel
              </button>
            </div>
          </>
        )}

        {/* ── VIEW EXISTING PROFILE (read-only) ── */}
        {!isEditable && !isEditingProfile && (
          <>
            {patient.location && (
              <div className="info-section">
                <div className="section-label">
                  <img src={ProfileIcon} alt="" className="icon" /> Location
                </div>
                <div className="section-content">{patient.location}</div>
              </div>
            )}
            <div className="info-section">
              <div className="section-label">
                <img src={CalendarIcon} alt="" className="icon" /> Last session
              </div>
              <div className="section-content">{patient.last_session || '—'}</div>
            </div>
            {patient.status && (
              <div className="info-section">
                <div className="section-label">
                  <img src={ProfileIcon} alt="" className="icon" /> Status
                </div>
                <div className="section-content">{patient.status}</div>
              </div>
            )}
          </>
        )}

        {/* ── CHECK-INS (existing patients only) ── */}
        {!isEditable && (
          <div>
            <div
              className="section-label"
              style={{ marginLeft: '20px', marginTop: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingRight: '20px' }}
            >
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <img src={ClockIcon} alt="" className="icon" />
                Upcoming Check-ins
              </span>
              <button
                type="button"
                onClick={handleAddNewCheckIn}
                style={{ fontSize: '12px', padding: '2px 8px', borderRadius: '4px', border: '1px solid #ccc', cursor: 'pointer', background: '#f0f0f0' }}
              >
                + Add
              </button>
            </div>

            {checkIns.length === 0 && newCheckIns.length === 0 && (
              <div style={{ margin: '8px 20px', color: '#999', fontSize: '13px' }}>
                No upcoming check-ins. Use "+ Add" to schedule one,<br />
                or use "Generate Check-ins" in the chat.
              </div>
            )}

            {checkIns.map((checkIn, index) => (
              <CheckInItem
                key={checkIn.id || index}
                checkIn={checkIn}
                onEdit={handleCheckInEdit}
              />
            ))}

            {newCheckIns.map((ci, index) => (
              <NewCheckInItem
                key={`new-${index}`}
                data={ci}
                index={index}
                onChange={handleNewCheckInChange}
                onRemove={handleRemoveNewCheckIn}
              />
            ))}
          </div>
        )}

        <div className="save-button-container">
          <button
            onClick={handleSaveAll}
            disabled={isSubmitting}
            type="button"
            className="save-button"
          >
            {isSubmitting ? 'Saving...' : (isEditable ? 'Create Member' : 'Save Check-in Changes')}
          </button>
        </div>
      </div>
    </form>
  );
};

/** Editable block for an existing check-in — no delete here, deletion is done from the calendar */
const CheckInItem = ({ checkIn, onEdit }) => {
  const formatDateForInput = (dateString) => {
    if (!dateString) return '';
    if (/^\d{4}-\d{2}-\d{2}$/.test(dateString)) return dateString;
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return '';
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  };

  const [editedCheckIn, setEditedCheckIn] = useState({
    checkInDate: formatDateForInput(checkIn.check_in),
    message: checkIn.follow_up_message || '',
  });

  const handleChange = (field, value) => {
    const updated = { ...editedCheckIn, [field]: value };
    setEditedCheckIn(updated);
    onEdit(checkIn.id, {
      check_in: field === 'checkInDate' ? value : editedCheckIn.checkInDate,
      follow_up_message: field === 'message' ? value : editedCheckIn.message,
    });
  };

  return (
    <div className="check-in-item" style={{ margin: '10px 20px', padding: '10px', border: '1px solid #e0e0e0', borderRadius: '8px', backgroundColor: '#f9f9f9' }}>
      <div style={{ fontWeight: 'bold', marginBottom: '5px', display: 'flex', alignItems: 'center' }}>
        <img src={ClockIcon} alt="" className="icon" style={{ width: '16px', marginRight: '5px' }} />
        <input
          type="date"
          value={editedCheckIn.checkInDate}
          onChange={(e) => handleChange('checkInDate', e.target.value)}
          style={{ border: '1px solid #ccc', padding: '5px', borderRadius: '4px' }}
        />
      </div>
      <div style={{ marginTop: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '5px' }}>
          <img src={ChatIcon} alt="" className="icon" style={{ width: '16px', marginRight: '5px' }} />
          <span style={{ fontSize: '14px', color: '#666' }}>Follow-up message</span>
        </div>
        <textarea
          value={editedCheckIn.message}
          onChange={(e) => handleChange('message', e.target.value)}
          style={{ width: '100%', minHeight: '60px', border: '1px solid #ccc', padding: '8px', borderRadius: '4px', resize: 'vertical', fontFamily: 'inherit', fontSize: '14px', boxSizing: 'border-box' }}
        />
      </div>
    </div>
  );
};

/** Form for a brand-new check-in being added */
const NewCheckInItem = ({ data, index, onChange, onRemove }) => (
  <div style={{ margin: '10px 20px', padding: '10px', border: '1px dashed #9F69AF', borderRadius: '8px', backgroundColor: '#faf5ff', position: 'relative' }}>
    <button
      type="button"
      onClick={() => onRemove(index)}
      style={{ position: 'absolute', top: '6px', right: '8px', background: 'none', border: 'none', cursor: 'pointer', color: '#c00', fontSize: '16px' }}
    >
      ×
    </button>
    <div style={{ fontSize: '12px', color: '#9F69AF', fontWeight: 'bold', marginBottom: '6px' }}>New Check-in</div>
    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
      <span style={{ fontSize: '13px', marginRight: '8px' }}>Date:</span>
      <input
        type="date"
        value={data.checkInDate}
        onChange={(e) => onChange(index, 'checkInDate', e.target.value)}
        style={{ border: '1px solid #ccc', padding: '5px', borderRadius: '4px' }}
      />
    </div>
    <div>
      <div style={{ fontSize: '13px', marginBottom: '4px', color: '#666' }}>Follow-up message</div>
      <textarea
        value={data.message}
        onChange={(e) => onChange(index, 'message', e.target.value)}
        placeholder="Enter message..."
        style={{ width: '100%', minHeight: '55px', border: '1px solid #ccc', padding: '8px', borderRadius: '4px', resize: 'vertical', fontFamily: 'inherit', fontSize: '14px', boxSizing: 'border-box' }}
      />
    </div>
  </div>
);

export default SidebarInformation;