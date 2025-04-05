import React, { useEffect, useState } from 'react';
import Sidebar from './Sidebar';
import '../styles/feature.css';

const ProfileManager = () => {
  const [allNames, setAllNames] = useState([{}]);
  const [hasSidebar, setSidebar] = useState(false);
  const [sidebarContent, setContent] = useState(null);
  const [search, setSearch] = useState('');

  // Step 2: Create the handler for input changes
  const handleSearchChange = (e) => {
    setSearch(e.target.value);  // Update the state with the input value
  };

  const getAllNames = async () => {
    const response = await fetch(`http://${window.location.hostname}:8000/service_user_list/?name=naveen`);
    response.json().then((res) => setAllNames(res));
  };

  useEffect(() => {
    getAllNames();
  }, []);

  let updateSidebar = (d) => {
    setSidebar(prevState => !prevState);  // Use functional form to toggle the sidebar state
    setContent(<div> 
        {d["service_user_name"]} <br />
        {d["location"]} <br />
      </div> )
  }

  return     <div class="container">
    <div className={`main-content ${hasSidebar ? 'shifted' : ''}`}>
    <input 
        type="text" 
        placeholder="Search Name, Date, etc." 
        className="search-box" 
        value={search}  // Set input value to the state
        onChange={handleSearchChange}  // Update state on change
      />  <table>
      <thead>
          <tr>
              <th>Name</th>
              <th>Location</th>
          </tr>
      </thead>
      <tbody>
          {allNames.map((d) => (d["location"]!=undefined && d["location"].toLowerCase().includes(search.toLowerCase()) || d["service_user_name"]!=undefined && d["service_user_name"].toLowerCase().includes(search.toLowerCase())) ? (<tr onClick={() => updateSidebar(d)}>
          <td>{d["service_user_name"]}</td>
          <td>{d["location"]}</td>
          </tr>) : "")}      
      </tbody>
  </table>
  </div> 
  <Sidebar isOpen={hasSidebar} content={sidebarContent} />
</div>
;
};

export default ProfileManager;
