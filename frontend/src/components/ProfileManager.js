// ProfileManager.js
import React, { useEffect, useState, useContext, useCallback, useMemo } from 'react';
import Sidebar from './Sidebar';
import AddIcon from '../icons/Add.png';
import SidebarInformation from './SidebarInformation';
import { useCheckIns } from '../hooks/useCheckIns';
import { WellnessContext } from './AppStateContextProvider';
import { apiPost, apiGet } from '../utils/api';
import { colorForStatus } from '../utils/colorUtils';

const INITIAL_FORM_STATE = {
  patientName: '',
  lastSession: '',
  nextCheckIn: '',
  followUpMessage: '',
  location: '',
  status: '',
};

const ProfileManager = () => {
  const { user } = useContext(WellnessContext);

  const [serviceUsers, setServiceUsers] = useState([]);
  const [hasSidebar, setSidebar] = useState(false);
  const [search, setSearch] = useState('');
  const [currentPatient, setCurrentPatient] = useState({});
  const [isEditable, setIsEditable] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [formData, setFormData] = useState(INITIAL_FORM_STATE);

  const {
    checkIns,
    fetchCheckIns,
    saveAllCheckIns,
    updatePatientLastSession,
  } = useCheckIns();

  useEffect(() => {
    if (currentPatient?.service_user_id && !isEditable) {
      fetchCheckIns(currentPatient.service_user_id);
    }
  }, [currentPatient?.service_user_id, isEditable, fetchCheckIns]);

  const fetchServiceUsers = useCallback(async () => {
    if (!user?.username) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiGet('/service_user_list/');
      setServiceUsers(data || []);
    } catch (err) {
      console.error('[ProfileManager] Error fetching users:', err);
      setError(err.message);
      setServiceUsers([]);
    } finally {
      setIsLoading(false);
    }
  }, [user?.username]);

  useEffect(() => { fetchServiceUsers(); }, [fetchServiceUsers]);

  const filteredServiceUsers = useMemo(() => {
    if (!search.trim()) return serviceUsers;
    const searchLower = search.toLowerCase();
    return serviceUsers.filter((u) => {
      const name = u.service_user_name?.toLowerCase() || '';
      const location = u.location?.toLowerCase() || '';
      return name.includes(searchLower) || location.includes(searchLower);
    });
  }, [serviceUsers, search]);

  const handleSearchChange = useCallback((e) => setSearch(e.target.value), []);
  const handleFormChange = useCallback((field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  }, []);

  const openSidebar = useCallback((patient, editable) => {
    setCurrentPatient(patient);
    setIsEditable(editable);
    setFormData(editable ? INITIAL_FORM_STATE : {
      patientName: patient.service_user_name || '',
      lastSession: patient.last_session || '',
      nextCheckIn: patient.check_in || '',
      followUpMessage: patient.follow_up_message || '',
      location: patient.location || '',
      status: patient.status || '',
    });
    setSidebar(true);
  }, []);

  const closeSidebar = useCallback(() => {
    setSidebar(false);
    setCurrentPatient(null);
    setIsEditable(false);
    setFormData(INITIAL_FORM_STATE);
  }, []);

  const handleSubmit = useCallback(async () => {
    setIsSubmitting(true);
    try {
      await apiPost('/new_service_user/', { ...formData, username: user.username });
      await fetchServiceUsers();
      closeSidebar();
    } catch (err) {
      alert(`Failed to create service user: ${err.message || 'Unknown error'}`);
    } finally {
      setIsSubmitting(false);
    }
  }, [formData, user.username, fetchServiceUsers, closeSidebar]);

  const handleUpdatePatient = async (updatedData) => {
    setIsSubmitting(true);
    try {
      if (updatedData.last_session !== undefined) {
        await updatePatientLastSession(currentPatient.service_user_id, updatedData.last_session);
      }
      const patchPayload = {};
      if (updatedData.service_user_name !== undefined) patchPayload.patientName = updatedData.service_user_name;
      if (updatedData.location !== undefined) patchPayload.location = updatedData.location;
      if (updatedData.status !== undefined) patchPayload.status = updatedData.status;

      if (Object.keys(patchPayload).length > 0) {
        await apiPost('/update_service_user/', {
          service_user_id: currentPatient.service_user_id,
          ...patchPayload,
        });
      }

      setCurrentPatient(prev => ({
        ...prev,
        service_user_name: updatedData.service_user_name ?? prev.service_user_name,
        location: updatedData.location ?? prev.location,
        status: updatedData.status ?? prev.status,
        last_session: updatedData.last_session ?? prev.last_session,
      }));

      await fetchServiceUsers();
      alert('Profile saved successfully!');
    } catch (error) {
      alert(`Failed to update: ${error.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveAllCheckIns = async (allEdits, deletions, additions) => {
    setIsSubmitting(true);
    try {
      await saveAllCheckIns(allEdits, currentPatient.service_user_id, deletions, additions);
      await fetchCheckIns(currentPatient.service_user_id);
      await fetchServiceUsers();
      alert('All changes saved successfully!');
    } catch (error) {
      alert(`Failed to update check-ins: ${error.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="container">
      <div className={`main-content ${hasSidebar ? 'shifted' : ''}`}>
        <div className="search-container">
          <input
            type="text"
            placeholder="Search by name or location..."
            className="profile-search-box"
            value={search}
            onChange={handleSearchChange}
            aria-label="Search service users"
          />
          <button className="add" onClick={() => openSidebar({}, true)} aria-label="Add new service user">
            <img src={AddIcon} alt="" />
            Add
          </button>
        </div>

        {/* Status legend */}
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', padding: '8px 0 4px', flexWrap: 'wrap' }}>
          {[['Active', '#79C981'], ['Inactive', '#E57C7E'], ['Pending', '#FFBC2A']].map(([label, color]) => (
            <span key={label} style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '13px' }}>
              <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: color, display: 'inline-block' }} />
              {label}
            </span>
          ))}
        </div>

        <div className="table-wrapper">
          {isLoading ? (
            <div className="loading-message">Loading service users...</div>
          ) : error ? (
            <div className="error-message">
              <p>Error: {error}</p>
              <button onClick={fetchServiceUsers}>Retry</button>
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Location</th>
                  <th>Last Session</th>
                  <th>Next Check-in</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredServiceUsers.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="empty-message">
                      {search ? `No results found for "${search}"` : 'No service users found'}
                    </td>
                  </tr>
                ) : (
                  filteredServiceUsers.map((u) => (
                    <tr
                      key={u.service_user_id || u.id}
                      onClick={() => openSidebar(u, false)}
                      className="clickable-row"
                    >
                      <td style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{
                          display: 'inline-block',
                          width: '10px',
                          height: '10px',
                          borderRadius: '50%',
                          background: colorForStatus(u.status),
                          flexShrink: 0,
                        }} />
                        {u.service_user_name || '—'}
                      </td>
                      <td>{u.location || '—'}</td>
                      <td>{u.last_session || '—'}</td>
                      <td>{u.check_in || '—'}</td>
                      <td>
                        <span style={{
                          padding: '2px 8px',
                          borderRadius: '12px',
                          fontSize: '12px',
                          background: colorForStatus(u.status) + '33', // 20% opacity
                          color: colorForStatus(u.status),
                          fontWeight: 600,
                        }}>
                          {u.status || '—'}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <Sidebar
        isOpen={hasSidebar}
        content={
          hasSidebar ? (
            <SidebarInformation
              checkIns={checkIns}
              patient={currentPatient}
              isEditable={isEditable}
              isSubmitting={isSubmitting}
              onSubmit={handleSubmit}
              formData={formData}
              onFormChange={handleFormChange}
              onUpdatePatient={handleUpdatePatient}
              onSaveAllCheckIns={handleSaveAllCheckIns}
              onClose={() => setSidebar(false)}
            />
          ) : null
        }
      />
    </div>
  );
};

export default ProfileManager;