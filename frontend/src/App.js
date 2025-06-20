import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import Navbar from './components/Navbar';
import Home from './components/Home';
import {WellnessGoals} from './components/GenericChat';
import {WellnessContextProvider} from './components/AppStateContextProvider.js';
import './App.css';

function App() {
  return (
    <WellnessContextProvider>
      <Router>
        <div className="App">
          <Navbar />
          <div className="content">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/wellness-goals" element={<WellnessGoals />} />
            </Routes>
          </div>
        </div>
      </Router>
    </WellnessContextProvider>
  );
}

export default App;
