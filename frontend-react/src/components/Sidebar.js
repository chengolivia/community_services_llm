import React, { useEffect, useState } from 'react';
import '../styles/sidebar.css';

const Sidebar = ({isOpen,content}) => {
    return  <div className={`sidebar ${isOpen ? 'open' : ''}`}>
        {content}
  </div>

};

export default Sidebar;
