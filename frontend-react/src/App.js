import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import Navbar from './components/Navbar';
import Home from './components/Home';
import WellnessGoals from './components/WellnessGoals';
import ResourceDatabase from './components/ResourceDatabase';
import BenefitEligibility from './components/BenefitEligibility';
import {WellnessContextProvider, BenefitContextProvider, ResourceContextProvider} from './components/AppStateContextProvider.js';
import './App.css';

function App() {
  return (
    <WellnessContextProvider>
      <BenefitContextProvider>
        <ResourceContextProvider>
          <Router>
            <div className="App">
              <Navbar />
              <div className="content">
                <Routes>
                  <Route path="/" element={<Home />} />
                  <Route path="/wellness-goals" element={<WellnessGoals />} />
                  <Route path="/resource-database" element={<ResourceDatabase />} />
                  <Route path="/benefit-eligibility" element={<BenefitEligibility />} />
                </Routes>
              </div>
            </div>
          </Router>
        </ResourceContextProvider>
      </BenefitContextProvider>
    </WellnessContextProvider>
  );
}

export default App;
