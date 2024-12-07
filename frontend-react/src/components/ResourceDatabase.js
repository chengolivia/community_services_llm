import React, { useState, useRef, useEffect } from 'react';
import '../styles/feature.css';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import ReactMarkdown from 'react-markdown';

function ResourceRecommendation() {
  const [inputText, setInputText] = useState('');
  const [inputLocationText, setInputLocationText] = useState('');
  const [newMessage, setNewMessage] = useState('');
  const [conversation, setConversation] = useState([]);
  const [submitted, setSubmitted] = useState(false);
  const [activeTab, setActiveTab] = useState('wellnessgoals');
  const [resources, setResources] = useState([]);
  const [chatConvo, setchatConvo] = useState([]);
  const latestMessageRef = useRef(newMessage);

  const handleInputChange = (e) => {
    setInputText(e.target.value);
  };

  const handleInputChangeLocation = (e) => {
    setInputLocationText(e.target.value)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  useEffect(() => {
    latestMessageRef.current = newMessage;
  }, [newMessage])


  const handleSubmit = async () => {
    if (inputText.trim()) {
      // Add user message to the conversation
      let location = inputLocationText.trim();
      if(location.length < 2) {
        location = "New Jersey";
      }
      const userMessage = { sender: 'user', text: inputText.trim()};
      setConversation((prev) => [...prev, userMessage]);
      setInputText('');

      await fetchEventSource(`http://127.0.0.1:8000/resource_response/`, {
        method: "POST",
        headers: { Accept: "text/event-stream",         
                  'Content-Type': 'application/json', },
        body: JSON.stringify({
          "text": userMessage.text +"\n Location: "+location, 
          "previous_text": chatConvo
        }),
        onopen(res) {
          if (res.ok && res.status === 200) {
            setchatConvo((prev) => [...prev,{'role': 'user','content': inputText.trim()}])
            setNewMessage("");
            
            const botMessage = {
              sender: "bot",
              text: "Loading...", 
            };
            setConversation((prev) => [...prev, botMessage]);
          } else if (res.status >= 400 && res.status < 500 && res.status !== 429) {
            console.log("Client-side error ", res);
          }
        },
        onmessage(event) {
          setNewMessage((prev) => {
            const updatedMessage = prev + event.data.replaceAll("<br/>","\n");
            console.log(updatedMessage)
            const botMessage = {
              sender: "bot",
              text: updatedMessage, // Use the updated message
            };
            setConversation((convPrev) => {
              if (convPrev.length > 0) {
                return [...convPrev.slice(0, -1), botMessage];
              }
              return [botMessage];
            });
        
            return updatedMessage; // Return the updated newMessage state
          });
        
        },
        onclose() {
          setchatConvo((prev) => [...prev,{'role': 'system','content': latestMessageRef.current}])
        },
        onerror(err) {
          console.log("There was an error from server", err);
        },
      });
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
              <ReactMarkdown children={msg.text} />
            </div>
          ))}
        </div>
        <div className={`input-section ${submitted ? 'input-bottom' : ''}`}>
          <div className="input-box">
          <textarea
              className="input-bar"
              placeholder={
                'Enter location (city or county)'
              }
              value={inputLocationText}
              onChange={handleInputChangeLocation}
              rows={1}
            /> 

          </div>
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
