import React, { useState } from 'react';
import '../styles/feature.css';

function ResourceRecommendation() {
  const [inputText, setInputText] = useState('');
  const [conversation, setConversation] = useState([]);
  const [submitted, setSubmitted] = useState(false);
  const [activeTab, setActiveTab] = useState('wellnessgoals');
  const [wellnessgoals, setwellnessgoals] = useState([]);

  const handleInputChange = (e) => {
    setInputText(e.target.value);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
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


      //The generated content should show up here
      const newwellnessgoals = [
        {
          title: 'Division of Mental Health & Addictions Services (DMHAS)',
          phone: '1-800-382-6717',
          website: 'https://www.samhsa.gov/find-help/national-helpline',
          description: 'SAMHSA’s National Helpline is a free, confidential, 24/7 service.',
          reason: `DMHAS provides excellent support for concerns similar to: "${inputText.trim()}".`,
        },
      ];
      setwellnessgoals(newwellnessgoals);
      setInputText('');
      setSubmitted(true);
    }
  };


  return (
    <div className="resource-recommendation-container">
      {/* Left Section */}
      <div className={`left-section ${submitted ? 'submitted' : ''}`}>
        <h1 className="page-title">Wellness Goals</h1>
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
              rows={1}
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
            className={`tab-button ${activeTab === 'wellnessgoals' ? 'active' : ''}`}
            onClick={() => setActiveTab('wellnessgoals')}
          >
            Wellness Goals
          </button>
          <button
            className={`tab-button ${activeTab === 'profile' ? 'active' : ''}`}
            onClick={() => setActiveTab('profile')}
          >
            Client profile
          </button>
        </div>
        <div className="tab-content">
          {activeTab === 'wellnessgoals' && (
            <div>
              <p>
                Wellness goals are recommended based on the client information from your
                meeting notes. Get more tailored recommendations by sending additional
                client information in the chat.
              </p>
              {wellnessgoals.map((resource, index) => (
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

          {/* Updated client profile below */}
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
