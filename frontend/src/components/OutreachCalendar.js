import React, { useEffect, useState } from 'react';
import '../styles/calendar.css';
import Sidebar from './Sidebar';
import '../styles/feature.css';

const OutreachCalendar = () => {
    const [weekCode, setWeekCode] = useState(null);
    const [hasSidebar, setSidebar] = useState(false);
    const [sidebarContent, setContent] = useState(null);
    const [search, setSearch] = useState('');
    const [allOutreach, setAllOutreach] = useState([]);

    // Step 2: Create the handler for input changes
    const handleSearchChange = (e) => {
        setSearch(e.target.value);  // Update the state with the input value
    };

    const updateOutreach = (all_outreach) => {
        let outreach_by_week = {};
        let colors = ["#FFBC2A","#9F69AF","#F5511F","#79C981","#34A2ED","#5AD1D3","#E57C7E","#FF61B5","#FFD83E","#FFAE95"]
        let idx_color = 0;
        let color_by_week = {}
    
        for (let i = 0; i < all_outreach.length; i++) {
            let curr_date = new Date();
            const dateList = all_outreach[i]["check_in"].split("-").map(Number);
            curr_date.setFullYear(dateList[2], dateList[0] - 1, dateList[1]);
            var a = curr_date.getDate();
            var t = curr_date.getDay();
            curr_date.setDate(a - t);
    
            let week_num = curr_date.getTime() / 1000;
    
            if (!(week_num in outreach_by_week)) {
                outreach_by_week[week_num] = [];
                color_by_week[week_num] = [];
            }
            outreach_by_week[week_num].push(all_outreach[i]); 
            color_by_week[week_num].push(colors[idx_color % colors.length]);
            idx_color++;
        }
    
        let all_weeks = Object.keys(outreach_by_week).sort();
        let week_code = [];
    
        const all_months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    
        for (let i = 0; i < all_weeks.length; i++) {
            let week_start = new Date(all_weeks[i] * 1000);
            let day_of_week = "Sunday";  // You can calculate day_of_week if needed
            let month = all_months[week_start.getMonth()];
            let date = week_start.getDate();
            
            // Filter the outreach list based on the search term
            const outreach_code = outreach_by_week[all_weeks[i]]
                .filter((d) => d["name"].toLowerCase().includes(search.toLowerCase()))
                .map((d, idx) => (
                    <li key={d.id} onClick={() => updateSidebar(d)}>
                        <span className="dot" style={{ background: color_by_week[all_weeks[i]][idx] }}></span>
                        Follow-up Wellness Check-in w/ {d["name"]}
                    </li>
                ));
    
            week_code.push(
                <div key={all_weeks[i]} className="day">
                    <div className="date black">{date}</div>
                    <div className="info">{month}, {day_of_week}</div>
                    <ul>
                        {outreach_code}
                    </ul>
                </div>
            );
        }
        setWeekCode(week_code);
    };

    const getAllOutreach = async () => {
        const response = await fetch(`http://${window.location.hostname}:8000/outreach_list/?name=naveen`);
        response.json().then((res) => {
            setAllOutreach(res); // Save the fetched data
            updateOutreach(res); // Process the data
        });
    };
  
    useEffect(() => {
        getAllOutreach();
    }, []);

    // Re-run updateOutreach whenever the search term changes
    useEffect(() => {
        if (allOutreach.length > 0) {
            updateOutreach(allOutreach);
        }
    }, [search, allOutreach]);  // Dependency array includes 'search' and 'allOutreach'

    let updateSidebar = (d) => {
        setSidebar(prevState => !prevState);  // Use functional form to toggle the sidebar state
        setContent(<div> 
            <h1> {d["name"]} </h1> 
            Last Session: {d["last_session"]}
        </div>);
    };

    return (
        <div className="container">
            <div className={`main-content ${hasSidebar ? 'shifted' : ''}`}>
                <div  className="header">
                    <h2 style={{paddingRight: "20px"}}>February 2025</h2>                     <input 
                        type="text" 
                        placeholder="Search" 
                        className="search-box" 
                        value={search}  // Set input value to the state
                        onChange={handleSearchChange}  // Update state on change
                    /> 

                </div>
            
                <div className="schedule">
                    {weekCode}
                </div> 
            </div> 
            <Sidebar isOpen={hasSidebar} content={sidebarContent} />
        </div>
    );
};

export default OutreachCalendar;