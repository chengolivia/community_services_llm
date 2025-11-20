import React, { useEffect, useState, useContext } from 'react';
import Sidebar from './Sidebar';
import '../styles/feature.css';
import AddIcon from '../icons/Add.png';
import SidebarInformation from './SidebarInformation';
import { WellnessContext } from './AppStateContextProvider';
import { API_URL } from '../config';



const ProfileManager = () => {
  const [allNames, setAllNames] = useState([{}]);
  const [hasSidebar, setSidebar] = useState(false);
  const [search, setSearch] = useState('');
  const { user } = useContext(WellnessContext);

  // Form state
  const [currentPatient, setCurrentPatient] = useState({});
  const [isEditable, setIsEditable] = useState(false);
  const [patientName, setPatientName] = useState('');
  const [lastSession, setLastSession] = useState('');
  const [nextCheckIn, setNextCheckIn] = useState('');
  const [followUpMessage, setFollowUpMessage] = useState('');
  const [checkIns, setCheckIns] = useState([]);
  const [pendingCheckInEdits, setPendingCheckInEdits] = useState({});

  useEffect(() => {
    if (currentPatient?.service_user_id && !isEditable) {
      fetch(`${API_URL}/service_user_check_ins/?service_user_id=${currentPatient.service_user_id}`)
        .then(res => res.json())
        .then(data => setCheckIns(data))
        .catch(error => {
          console.error('[Check-ins] Error fetching:', error);
          setCheckIns([]);
        });
    } else {
      setCheckIns([]);
    }
  }, [currentPatient?.service_user_id, isEditable]);
  

  const handleSearchChange = (e) => {
    setSearch(e.target.value);
  };

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const handleSubmit = async () => {
    // Process form data
    console.log('[Submit] Starting:', { patientName, lastSession, nextCheckIn });
    setIsSubmitting(true);
    
    try {
      const response = await fetch(`${API_URL}/new_service_user/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          patientName,
          lastSession,
          nextCheckIn,
          followUpMessage,
          username: user.username
        }),
      });
  
      const result = await response.json();
      console.log("[Submit] Response:", result);

    
    if (!response.ok) {
      throw new Error(result.detail || 'Failed to save')
    }

    alert('Check-in saved!');

    // Refresh list
    await getAllNames();
    
    // Close and reset
    setSidebar(false);
    setPatientName('');
    setLastSession('');
    setNextCheckIn('');
    setFollowUpMessage('');
    } catch (error) {
      console.error("Error:", error);
      alert(`Failed: ${error.followUpMessage}`)
    } finally {
      setIsSubmitting(false);
    }
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
    setIsLoading(true);
    try {
      const response = await fetch(`${API_URL}/service_user_list/?name=${user.username}`);
      const res = await response.json()
      setAllNames(res);
      console.log('[Load] Got', res.length, 'profiles');
    } catch (error) {
      console.error('[Load] Error:', error);
      setAllNames([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    getAllNames();
  }, [user.username]);

  const handleUpdatePatient = async (updatedData) => {
    setIsSubmitting(true);
    try {
      // Update patient's last session
      if (updatedData.last_session !== undefined) {
        const response = await fetch(`${API_URL}/service_user/${currentPatient.service_user_id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            last_session: updatedData.last_session
          })
        });

        if (!response.ok) {
          throw new Error('Failed to update patient');
        }

        // Update local state
        setCurrentPatient(prev => ({
          ...prev,
          last_session: updatedData.last_session
        }));
        setLastSession(updatedData.last_session);
      }

      // Refresh the list
      await getAllNames();
      
      alert('Changes saved successfully!');
    } catch (error) {
      console.error('Error updating patient:', error);
      alert(`Failed to update: ${error.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveAllCheckIns = async (allEdits) => {
    setIsSubmitting(true);
    try {
      // Save all modified check-ins
      for (const [id, data] of Object.entries(allEdits)) {
        const response = await fetch(`${API_URL}/service_user_check_ins/${id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            check_in: data.check_in,
            follow_up_message: data.follow_up_message
          })
        });

        if (!response.ok) {
          throw new Error(`Failed to update check-in ${id}`);
        }
      }

      // Refresh check-ins after all updates
      const checkInsResponse = await fetch(`${API_URL}/service_user_check_ins/?service_user_id=${currentPatient.service_user_id}`);
      const updatedCheckIns = await checkInsResponse.json();
      setCheckIns(updatedCheckIns);

      alert('All changes saved successfully!');
      setPendingCheckInEdits({}); // Clear pending edits
    } catch (error) {
      console.error('Error updating check-ins:', error);
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
            placeholder="Search Name, Date, etc." 
            className="profile-search-box" 
            value={search}
            onChange={handleSearchChange}
          />
          <button className="add" onClick={() => openSidebar({}, true)}>
            <img src={AddIcon} alt="Add Icon" /> Add
          </button>
        </div>
        <div className="table-wrapper">
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
            onUpdatePatient={handleUpdatePatient}
            onSaveAllCheckIns={handleSaveAllCheckIns}
            pendingCheckInEdits={pendingCheckInEdits}
            setPendingCheckInEdits={setPendingCheckInEdits}
            onClose={() => setSidebar(false)}
            patientName={patientName}
            setPatientName={setPatientName}
            lastSession={lastSession}
            setLastSession={setLastSession}
          />
        ) : null
      }
    />

    </div>
  );
};

export default ProfileManager;