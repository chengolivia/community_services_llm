import React, { useState } from 'react';
import '../styles/feature.css';

function ResourceRecommendation() {
  const [inputText, setInputText] = useState('');
  const [conversation, setConversation] = useState([]);
  const [submitted, setSubmitted] = useState(false);
  const [activeTab, setActiveTab] = useState('benefits');
  const [benefits, setbenefits] = useState([]);

  const handleInputChange = (e) => {
    setInputText(e.target.value);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault(); // Prevent new line
      handleSubmit(); // Submit input
    }
  };

  const handleSubmit = () => {
    if (inputText.trim()) {
      const userMessage = { sender: 'user', text: inputText.trim() };
      const botMessage = {
        sender: 'bot',
        text: `Thank you for sharing! Here's what we found based on your input: "${inputText.trim()}".`,
      };

      setConversation([...conversation, userMessage, botMessage]);

      // Update benefits list
      const newbenefits = [
        {
          category: 'Highly Eligible',
          phone: '1-800-772-1213',
          website: 'https://www.nj.gov/humanservices/dfd/programs/ssi/',
          description:
            'Supplemental Security Income (SSI) for Single Adults',
          reason: `The user meets all the eligibility criteria for SSI as a single adult. They have an income less than $1,971 per month from work, and their resources are less than $2,000.`,
        },
        {
          category: 'Likely Eligible',
          phone: '1-800-772-1213',
          website: 'https://www.ssa.gov/',
          description: 'Social Security Administration (SSA)',
          reason: `The user has been working for the past 12 years, which should give them 48 credits, assuming they’ve been earning at least $1,730 per year. This makes them eligible for the SSA, considering that a minimum of 40 credits is required. However, the actual earnings and credits need to be confirmed.`,
        },
        {
          category: 'Maybe Eligible',
          phone: '1-732-243-0311',
          website: 'https://njmedicare.com/',
          description:
            'Benefits 3 & 4: Medicare Part A & B, and Social Security Disability Insurance (SSDI)',
          reason: `For Medicare, the user meets the age requirement for eligibility. However, further details regarding their health status may be required to determine SSDI eligibility.`,
        },
      ];
      setbenefits(newbenefits);

      setInputText('');
      setSubmitted(true);
    }
  };


  return (
    <div className="resource-recommendation-container">
      {/* Left Section */}
      <div className={`left-section ${submitted ? 'submitted' : ''}`}>
        <h1 className="page-title">Benefit Eligibility</h1>
        <h2 className="instruction">
          What is your client’s needs and goals for today’s meeting?
        </h2>
        <div className={`conversation-thread ${submitted ? 'visible' : ''}`}>
          {conversation.map((msg, index) => (
            <div
              key={index}
              className={`message-blurb ${msg.sender === 'user' ? 'user' : 'bot'}`}
            >
              {msg.text}
            </div>
          ))}
        </div>
        <div className={`input-section ${submitted ? 'input-bottom' : ''}`}>
          <div className="input-box">
            <textarea
              className="input-bar"
              placeholder={
                submitted ? 'Write a follow-up to update...' : 'Describe your client’s situation...'
              }
              value={inputText}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              rows={1} // Auto-resize if needed
            />
            <button className="voice-icon">🎤</button>
            <button className="submit-button" onClick={handleSubmit}>
              ➤
            </button>
          </div>
        </div>
      </div>

      {/* Right Section */}
      <div className="right-section">
        <div className="tabs">
          <button
            className={`tab-button ${activeTab === 'benefits' ? 'active' : ''}`}
            onClick={() => setActiveTab('benefits')}
          >
            Recommended benefits
          </button>
          <button
            className={`tab-button ${activeTab === 'profile' ? 'active' : ''}`}
            onClick={() => setActiveTab('profile')}
          >
            Client profile
          </button>
        </div>
        <div className="tab-content">
          {activeTab === 'benefits' && (
            <div>
              <p>
                benefits are recommended based on the client information from your
                meeting notes. Get more tailored recommendations by sending additional
                client information in the chat.
              </p>
              {benefits.map((resource, index) => (
                <div key={index} className="resource-item">
                  <h3>{resource.title}</h3>
                  <p><strong>Phone:</strong> {resource.phone}</p>
                  <p>
                    <strong>Website:</strong>{' '}
                    <a href={resource.website} target="_blank" rel="noopener noreferrer">
                      {resource.website}
                    </a>
                  </p>
                  <p><strong>Description:</strong> {resource.description}</p>
                  <p><strong>Reason:</strong> {resource.reason}</p>
                </div>
              ))}
            </div>
          )}
          {activeTab === 'profile' && (
            <div>
              <p>
                Client profile information is extracted from the meeting notes you send in
                chat. Edit by sending updated information in the chat.
              </p>
              <h3>Client needs</h3>
              <p><strong>Goals:</strong> Lorem ipsum dolor sit amet consectetur. Fames lacinia sapien elementum diam tellus. Aliquet nulla purus nibh suspendisse sit in sed aliquam commodo.</p>
              <p><strong>Immediate needs:</strong> Lorem ipsum dolor sit amet consectetur. Fames lacinia sapien elementum diam tellus. Aliquet nulla purus nibh suspendisse sit in sed aliquam commodo.</p>
              <h3>Demographics</h3>
              <ul>
                <li><strong>County:</strong> Lorem ipsum</li>
                <li><strong>Age:</strong> Lorem ipsum</li>
                <li><strong>Housing status:</strong> Lorem ipsum</li>
                <li><strong>Other client info:</strong> Lorem ipsum</li>
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ResourceRecommendation;
