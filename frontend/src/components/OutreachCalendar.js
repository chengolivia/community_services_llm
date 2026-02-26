// OutreachCalendar.js - Calendar view showing scheduled check-ins
import React, { useEffect, useState, useContext, useCallback, useMemo } from 'react';
import Sidebar from './Sidebar';
import SidebarInformation from './SidebarInformation';
import { WellnessContext } from './AppStateContextProvider';
import { useCheckIns } from '../hooks/useCheckIns';
import { apiGet } from '../utils/api';
import { colorForStatus } from '../utils/colorUtils';
import '../styles/pages/calendar.css';

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];
const DAYS_OF_WEEK = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

const parseCheckInDate = (checkInStr) => {
  if (!checkInStr) return null;
  const parts = checkInStr.split('-').map(Number);
  if (parts[0] > 31) {
    const [year, month, day] = parts;
    return new Date(year, month - 1, day);
  }
  const [month, day, year] = parts;
  return new Date(year, month - 1, day);
};

const getDateKey = (date) =>
  `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;

const OutreachCalendar = () => {
  const { user } = useContext(WellnessContext);

  const [search, setSearch] = useState('');
  const [allOutreach, setAllOutreach] = useState([]);
  const [currentPatient, setCurrentPatient] = useState(null);
  const [hasSidebar, setSidebar] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [completingId, setCompletingId] = useState(null);

  const {
    checkIns,
    fetchCheckIns,
    saveAllCheckIns,
    updatePatientLastSession,
  } = useCheckIns();
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (currentPatient?.service_user_id) {
      fetchCheckIns(currentPatient.service_user_id);
    }
  }, [currentPatient?.service_user_id, fetchCheckIns]);

  const fetchOutreach = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      // Use outreach_list so we get one row per check-in (with check_in_id)
      // Falls back to service_user_list if outreach_list isn't available
      const data = await apiGet('/outreach_list/');
      console.log('[Calendar] Outreach data sample:', data[0]);
      setAllOutreach(data);
    } catch (err) {
      console.error('Error fetching outreach:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { fetchOutreach(); }, [fetchOutreach]);

  // Group outreach by date
  const outreachByDate = useMemo(() => {
    const grouped = {};
    allOutreach.forEach((outreach) => {
      const date = parseCheckInDate(outreach.check_in);
      if (!date || isNaN(date.getTime())) return;
      const dateKey = getDateKey(date);
      if (!grouped[dateKey]) grouped[dateKey] = { date, outreach: [] };
      grouped[dateKey].outreach.push({
        ...outreach,
        color: colorForStatus(outreach.status),
      });
    });
    return grouped;
  }, [allOutreach]);

  /**
   * Complete a single check-in from the calendar.
   * Uses check_in_id (the outreach_details.id PK), not service_user_id.
   */
  const handleCompleteCheckIn = useCallback(async (checkInId, e) => {
    e.stopPropagation();

    if (checkInId == null) {
      alert('Cannot complete this check-in: missing ID. Try refreshing the page.');
      return;
    }

    console.log('[Calendar] Completing check-in ID:', checkInId, typeof checkInId);

    if (!window.confirm('Mark this check-in as complete and remove it from the calendar?')) return;

    setCompletingId(checkInId);
    try {
      await saveAllCheckIns({}, null, [checkInId], []);
      await fetchOutreach();
    } catch (err) {
      alert(`Failed to complete check-in: ${err.message}`);
    } finally {
      setCompletingId(null);
    }
  }, [saveAllCheckIns, fetchOutreach]);

  const dateComponents = useMemo(() => {
    const sortedDates = Object.keys(outreachByDate).sort(
      (a, b) => outreachByDate[a].date.getTime() - outreachByDate[b].date.getTime()
    );
    const searchLower = search.toLowerCase();

    return sortedDates.map((dateKey) => {
      const { date, outreach } = outreachByDate[dateKey];
      const month = MONTHS[date.getMonth()];
      const day = date.getDate();
      const dayOfWeek = DAYS_OF_WEEK[date.getDay()];
      const year = date.getFullYear();

      const filteredOutreach = outreach.filter((item) => {
        const name = (item.name || item.service_user_name || '').toLowerCase();
        return name.includes(searchLower);
      });
      if (filteredOutreach.length === 0 && search) return null;

      return (
        <div key={dateKey} className="day">
          <div className="date black">{day}</div>
          <div className="info">{dayOfWeek}, {month} {day}, {year}</div>
          <ul>
            {filteredOutreach.map((item, idx) => {
              // check_in_id is the outreach_details PK — now returned by get_all_outreach
              const checkInId = item.check_in_id;
              const isCompleting = completingId === checkInId;

              return (
                <li
                  key={`${item.service_user_id}-${item.check_in}-${idx}`}
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}
                >
                  <span
                    style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', flex: 1 }}
                    onClick={() => handlePatientClick(item)}
                  >
                    <span className="dot" style={{ background: item.color, flexShrink: 0 }} />
                    Follow-up Wellness Check-in w/ {item.name || item.service_user_name}
                  </span>

                  <button
                    onClick={(e) => handleCompleteCheckIn(checkInId, e)}
                    disabled={isCompleting || checkInId == null}
                    title={checkInId == null ? 'No check-in ID available' : 'Mark as complete and remove'}
                    style={{
                      fontSize: '11px',
                      padding: '2px 8px',
                      borderRadius: '4px',
                      border: '1px solid #79C981',
                      background: checkInId == null ? '#eee' : '#f0fbf1',
                      color: checkInId == null ? '#aaa' : '#3a7d44',
                      cursor: checkInId == null ? 'not-allowed' : 'pointer',
                      whiteSpace: 'nowrap',
                      flexShrink: 0,
                    }}
                  >
                    {isCompleting ? '...' : '✓ Complete'}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      );
    }).filter(Boolean);
  }, [outreachByDate, search, completingId, handleCompleteCheckIn]);

  const handleSearchChange = useCallback((e) => setSearch(e.target.value), []);

  const handlePatientClick = useCallback((patient) => {
    setCurrentPatient(patient);
    setSidebar(true);
  }, []);

  const handleCloseSidebar = useCallback(() => {
    setSidebar(false);
    setCurrentPatient(null);
  }, []);

  const handleUpdatePatient = async (updatedData) => {
    setIsSubmitting(true);
    try {
      if (updatedData.last_session !== undefined) {
        await updatePatientLastSession(currentPatient.service_user_id, updatedData.last_session);
        setCurrentPatient(prev => ({ ...prev, ...updatedData }));
      }
      await fetchOutreach();
      alert('Profile saved successfully!');
    } catch (err) {
      alert(`Failed to update: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveAllCheckIns = async (allEdits, deletions, additions) => {
    setIsSubmitting(true);
    try {
      await saveAllCheckIns(allEdits, currentPatient.service_user_id, deletions, additions);
      await fetchOutreach();
      alert('All changes saved successfully!');
    } catch (err) {
      alert(`Failed to update check-ins: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const currentMonth = MONTHS[new Date().getMonth()];
  const currentYear = new Date().getFullYear();

  return (
    <div className="container">
      <div className={`main-content ${hasSidebar ? 'shifted' : ''}`}>
        <div className="header">
          <h2 style={{ paddingRight: '20px' }}>{currentMonth} {currentYear}</h2>

          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
            {[['Active', '#79C981'], ['Inactive', '#E57C7E'], ['Pending', '#FFBC2A'], ['Closed', '#AAAAAA']].map(([label, color]) => (
              <span key={label} style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '13px' }}>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: color, display: 'inline-block' }} />
                {label}
              </span>
            ))}
          </div>

          <input
            type="text"
            placeholder="Search by member name..."
            className="search-box"
            value={search}
            onChange={handleSearchChange}
            aria-label="Search members"
          />
        </div>

        <div className="table-wrapper">
          <div className="schedule">
            {isLoading && <div className="loading-message">Loading outreach data...</div>}
            {error && (
              <div className="error-message">
                Error: {error}
                <button onClick={fetchOutreach}>Retry</button>
              </div>
            )}
            {!isLoading && !error && dateComponents.length === 0 && (
              <div className="empty-message">
                {search ? `No results found for "${search}"` : 'No outreach scheduled'}
              </div>
            )}
            {!isLoading && !error && dateComponents}
          </div>
        </div>
      </div>

      <Sidebar
        isOpen={hasSidebar}
        content={
          hasSidebar && currentPatient ? (
            <SidebarInformation
              checkIns={checkIns}
              patient={currentPatient}
              isEditable={false}
              isSubmitting={isSubmitting}
              onSubmit={() => {}}
              onUpdatePatient={handleUpdatePatient}
              onSaveAllCheckIns={handleSaveAllCheckIns}
              onClose={handleCloseSidebar}
            />
          ) : null
        }
      />
    </div>
  );
};

export default OutreachCalendar;