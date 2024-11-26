import React, { useState } from 'react';
import axios from 'axios';
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

  const handleSubmit = async () => {
    if (inputText.trim()) {
      // Add user message to the conversation
      const userMessage = { sender: 'user', text: inputText.trim() };
      setConversation((prev) => [...prev, userMessage]);
  
      try {
        // Make an async call to the FastAPI endpoint
        const response = await axios.post('http://127.0.0.1:8000/benefit_response', {
          text: inputText.trim(),
        });
  
        // Assume response.data is the new benefits array
        const newBenefits = response.data;
  
        // Update bot message with the response and benefits
        const botMessage = {
          sender: 'bot',
          text: `Thank you for sharing! Here's what we found based on your input: "${inputText.trim()}".`,
        };
  
        setConversation((prev) => [...prev, botMessage]);
        setbenefits(newBenefits);
      } catch (error) {
        console.error('Error fetching benefits:', error);
  
        // Handle error gracefully in the conversation
        const errorMessage = {
          sender: 'bot',
          text: `Sorry, we encountered an error while processing your input. Please try again later.`,
        };
        setConversation((prev) => [...prev, errorMessage]);
      }
  
      // Reset input and set submitted state
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
              Benefit program results are recommended based on the client information from your meeting notes. Get more accurate results analysis by sending additional client information in the chat.
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
          {/* Update client info here */}
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
