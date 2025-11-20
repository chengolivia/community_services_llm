import React, { useEffect, useState, useContext, useCallback, useMemo } from 'react';
import Sidebar from './Sidebar';
import SidebarInformation from './SidebarInformation';
import { WellnessContext } from './AppStateContextProvider';
import { authenticatedFetch } from '../utils/api';
import '../styles/pages/calendar.css';
import { API_URL } from '../config';


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
  // Handle both YYYY-MM-DD and MM-DD-YYYY formats
  const parts = checkInStr.split('-').map(Number);
  
  // Check if first part is a year (4 digits) - YYYY-MM-DD format
  if (parts[0] > 31) {
    const [year, month, day] = parts;
    return new Date(year, month - 1, day);
  } else {
    // MM-DD-YYYY format
    const [month, day, year] = parts;
    return new Date(year, month - 1, day);
  }
};

const getDateKey = (date) => {
  // Create a key for the specific date (not week start)
  const year = date.getFullYear();
  const month = date.getMonth();
  const day = date.getDate();
  return `${year}-${month}-${day}`;
};


// const OutreachCalendar = () => {
//     const [weekCode, setWeekCode] = useState(null);
//     const [hasSidebar, setSidebar] = useState(false);
//     const [search, setSearch] = useState('');
//     const [allOutreach, setAllOutreach] = useState([]);
//     const [currentPatient, setCurrentPatient] = useState({});
//     const { user } = useContext(WellnessContext);
//     const [checkIns, setCheckIns] = useState([]);

//     useEffect(() => {
//         if (currentPatient?.service_user_id) {
//             fetch(`${API_URL}/service_user_check_ins/?service_user_id=${currentPatient.service_user_id}`)
//                 .then(res => res.json())
//                 .then(data => setCheckIns(data))
//                 .catch(error => {
//                     console.error('[Check-ins] Error fetching:', error);
//                     setCheckIns([]);
//                 });
//         } else {
//             setCheckIns([]);
//         }
//     }, [currentPatient?.service_user_id]);


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
      const response = await authenticatedFetch(`${API_URL}/service_user_check_ins/?service_user_id=${currentPatient.service_user_id}`);
      
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

  // Group outreach by actual date
  const outreachByDate = useMemo(() => {
    const grouped = {};
    const patientColors = {};
    let colorIndex = 0;

    allOutreach.forEach((outreach) => {
      const date = parseCheckInDate(outreach.check_in);
      
      // Skip invalid dates
      if (isNaN(date.getTime())) {
        console.warn('Invalid date for outreach:', outreach.check_in);
        return;
      }
      
      const dateKey = getDateKey(date);

      if (!grouped[dateKey]) {
        grouped[dateKey] = {
          date: date,
          outreach: []
        };
      }

      // Assign consistent color per patient
      if (!patientColors[outreach.name]) {
        patientColors[outreach.name] = COLORS[colorIndex % COLORS.length];
        colorIndex++;
      }

      grouped[dateKey].outreach.push({
        ...outreach,
        color: patientColors[outreach.name]
      });
    });

    return grouped;
  }, [allOutreach]);

  // Filter and render dates
  const dateComponents = useMemo(() => {
    const sortedDates = Object.keys(outreachByDate).sort((a, b) => {
      // Sort by actual date, oldest first
      return outreachByDate[a].date.getTime() - outreachByDate[b].date.getTime();
    });
    
    const searchLower = search.toLowerCase();

    return sortedDates.map((dateKey) => {
      const { date, outreach } = outreachByDate[dateKey];
      const month = MONTHS[date.getMonth()];
      const day = date.getDate();
      const dayOfWeek = DAYS_OF_WEEK[date.getDay()];

      const filteredOutreach = outreach.filter((item) =>
        item.name.toLowerCase().includes(searchLower)
      );

      // Skip dates with no matching results
      if (filteredOutreach.length === 0 && search) {
        return null;
      }

      const year = date.getFullYear();

      return (
        <div key={dateKey} className="day">
          <div className="date black">{day}</div>
          <div className="info">
            {dayOfWeek}, {month} {day}, {year}
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
  }, [outreachByDate, search]);

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

            {!isLoading && !error && dateComponents.length === 0 && (
              <div className="empty-message">
                {search
                  ? `No results found for "${search}"`
                  : 'No outreach scheduled'}
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
