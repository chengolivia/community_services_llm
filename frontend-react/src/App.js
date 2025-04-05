import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import Navbar from './components/Navbar';
import Home from './components/Home';
import {ResourceRecommendation,BenefitEligibility,WellnessGoals} from './components/GenericChat';
import ProfileManager from './components/ProfileManager';
import OutreachCalendar from './components/OutreachCalendar';
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
                  <Route path="/resource-database" element={<ResourceRecommendation />} />
                  <Route path="/benefit-eligibility" element={<BenefitEligibility />} />
                  <Route path="/profile-manager" element={<ProfileManager />} />
                  <Route path="/outreach-calendar" element={<OutreachCalendar />} />
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
