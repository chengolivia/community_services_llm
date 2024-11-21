import React, { useState } from 'react';
import '../styles/ResourceRecommendation.css';

function ResourceRecommendation() {
  const [inputText, setInputText] = useState('');
  const [conversation, setConversation] = useState([]);
  const [submitted, setSubmitted] = useState(false);
  const [activeTab, setActiveTab] = useState('resources');
  const [resources, setResources] = useState([]); // Store recommended resources

  const handleInputChange = (e) => {
    setInputText(e.target.value);
  };

  const handleSubmit = () => {
    if (inputText.trim()) {
      const userMessage = { sender: 'user', text: inputText.trim() };
      const botMessage = {
        sender: 'bot',
        text: `Thank you for sharing. Based on your input: "${inputText.trim()}", here are some suggestions.`,
      }; 

      // Update conversation
      setConversation([...conversation, userMessage, botMessage]);

      // Update resources
      const newResources = [
        {
          title: 'Division of Mental Health & Addictions Services (DMHAS)',
          phone: '1-800-382-6717',
          website: 'https://www.samhsa.gov/find-help/national-helpline',
          description: 'SAMHSA’s National Helpline is a free, confidential, 24/7, 365-day-a-year treatment referral service.',
          reason: `DMHAS can help with both mental health issues and addiction services for input: "${inputText.trim()}".`,
        },
      ];
      setResources(newResources); // Replace old suggestions with new ones

      setInputText('');
      setSubmitted(true);
    }
  };

  return (
    <div className="resource-recommendation-container">
      {/* Left Section */}
      <div className={`left-section ${submitted ? 'submitted' : ''}`}>
        <h1 className="page-title">Resource Database</h1>
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
            <input
              type="text"
              className="input-bar"
              placeholder={
                submitted ? 'Write a follow-up to update...' : 'Describe your client’s situation...'
              }
              value={inputText}
              onChange={handleInputChange}
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
            className={`tab-button ${activeTab === 'resources' ? 'active' : ''}`}
            onClick={() => setActiveTab('resources')}
          >
            Recommended resources
          </button>
          <button
            className={`tab-button ${activeTab === 'profile' ? 'active' : ''}`}
            onClick={() => setActiveTab('profile')}
          >
            Client profile
          </button>
        </div>
        <div className="tab-content">
          {activeTab === 'resources' && (
            <div>
              <p>
                Resources are recommended based on the client information from your
                meeting notes. Get more tailored recommendations by sending additional
                client information in the chat.
              </p>
              {resources.map((resource, index) => (
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
              <ul>
                {conversation
                  .filter((msg) => msg.sender === 'user')
                  .map((msg, index) => (
                    <li key={index}>
                      <strong>Input:</strong> {msg.text}
                    </li>
                  ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ResourceRecommendation;
