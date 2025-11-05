import React, { useEffect, useState, useContext, useCallback, useMemo } from 'react';
import Sidebar from './Sidebar';
import SidebarInformation from './SidebarInformation';
import { WellnessContext } from './AppStateContextProvider';
import { authenticatedFetch } from '../utils/api';
import '../styles/pages/calendar.css';

// Constants
const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

const COLORS = [
  '#FFBC2A', '#9F69AF', '#F5511F', '#79C981', '#34A2ED',
  '#5AD1D3', '#E57C7E', '#FF61B5', '#FFD83E', '#FFAE95'
];

const DAYS_OF_WEEK = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

// Utility functions
const parseCheckInDate = (checkInStr) => {
  const [month, day, year] = checkInStr.split('-').map(Number);
  return new Date(year, month - 1, day);
};

const getWeekStart = (date) => {
  const newDate = new Date(date);
  const dayOfWeek = newDate.getDay();
  newDate.setDate(newDate.getDate() - dayOfWeek);
  return newDate;
};

const getWeekTimestamp = (date) => {
  return Math.floor(date.getTime() / 1000);
};

const OutreachCalendar = () => {
  const { user } = useContext(WellnessContext);
  
  const [search, setSearch] = useState('');
  const [allOutreach, setAllOutreach] = useState([]);
  const [currentPatient, setCurrentPatient] = useState(null);
  const [hasSidebar, setSidebar] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch outreach data
  const fetchOutreach = useCallback(async () => {
    if (!user?.username) return;

    try {
      setIsLoading(true);
      setError(null);
      const response = await authenticatedFetch(`/outreach_list/?name=${user.username}`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch outreach data');
      }
      
      const data = await response.json();
      setAllOutreach(data);
    } catch (err) {
      console.error('Error fetching outreach:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, [user?.username]);

  useEffect(() => {
    fetchOutreach();
  }, [fetchOutreach]);

  // Group outreach by week
  const outreachByWeek = useMemo(() => {
    const grouped = {};
    const patientColors = {};
    let colorIndex = 0;

    allOutreach.forEach((outreach) => {
      const date = parseCheckInDate(outreach.check_in);
      const weekStart = getWeekStart(date);
      const weekKey = getWeekTimestamp(weekStart);

      if (!grouped[weekKey]) {
        grouped[weekKey] = [];
      }

      // Assign consistent color per patient
      if (!patientColors[outreach.name]) {
        patientColors[outreach.name] = COLORS[colorIndex % COLORS.length];
        colorIndex++;
      }

      grouped[weekKey].push({
        ...outreach,
        color: patientColors[outreach.name]
      });
    });

    return grouped;
  }, [allOutreach]);

  // Filter and render weeks
  const weekComponents = useMemo(() => {
    const sortedWeeks = Object.keys(outreachByWeek).sort((a, b) => b - a); // Most recent first
    const searchLower = search.toLowerCase();

    return sortedWeeks.map((weekKey) => {
      const weekStart = new Date(Number(weekKey) * 1000);
      const month = MONTHS[weekStart.getMonth()];
      const date = weekStart.getDate();
      const dayOfWeek = DAYS_OF_WEEK[weekStart.getDay()];

      const filteredOutreach = outreachByWeek[weekKey].filter((item) =>
        item.name.toLowerCase().includes(searchLower)
      );

      // Skip weeks with no matching results
      if (filteredOutreach.length === 0 && search) {
        return null;
      }

      return (
        <div key={weekKey} className="day">
          <div className="date black">{date}</div>
          <div className="info">
            {month}, {dayOfWeek}
          </div>
          <ul>
            {filteredOutreach.map((item) => (
              <li key={item.id} onClick={() => handlePatientClick(item)}>
                <span className="dot" style={{ background: item.color }} />
                Follow-up Wellness Check-in w/ {item.name}
              </li>
            ))}
          </ul>
        </div>
      );
    }).filter(Boolean); // Remove null entries
  }, [outreachByWeek, search]);

  // Handlers
  const handleSearchChange = useCallback((e) => {
    setSearch(e.target.value);
  }, []);

  const handlePatientClick = useCallback((patient) => {
    setCurrentPatient({
      service_user_name: patient.name || '',
      last_session: patient.last_session || '',
      check_in: patient.check_in || '',
      follow_up_message: patient.follow_up_message || ''
    });
    setSidebar(true);
  }, []);

  const handleCloseSidebar = useCallback(() => {
    setSidebar(false);
    setCurrentPatient(null);
  }, []);

  // Get current date info
  const currentMonth = MONTHS[new Date().getMonth()];
  const currentYear = new Date().getFullYear();

  return (
    <div className="container">
      <div className={`main-content ${hasSidebar ? 'shifted' : ''}`}>
        <div className="header">
          <h2 style={{ paddingRight: '20px' }}>
            {currentMonth} {currentYear}
          </h2>
          <input
            type="text"
            placeholder="Search by patient name..."
            className="search-box"
            value={search}
            onChange={handleSearchChange}
            aria-label="Search patients"
          />
        </div>

        <div className="table-wrapper">
          <div className="schedule">
            {isLoading && (
              <div className="loading-message">Loading outreach data...</div>
            )}
            
            {error && (
              <div className="error-message">
                Error: {error}
                <button onClick={fetchOutreach}>Retry</button>
              </div>
            )}

            {!isLoading && !error && weekComponents.length === 0 && (
              <div className="empty-message">
                {search
                  ? `No results found for "${search}"`
                  : 'No outreach scheduled'}
              </div>
            )}

            {!isLoading && !error && weekComponents}
          </div>
        </div>
      </div>

      <Sidebar
        isOpen={hasSidebar}
        content={
          hasSidebar && currentPatient ? (
            <SidebarInformation
              patient={currentPatient}
              isEditable={false}
              onSubmit={() => {}}
              onClose={handleCloseSidebar}
            />
          ) : null
        }
      />
    </div>
  );
};

export default OutreachCalendar;