import React, { useState, useRef, useEffect } from 'react';
import '../styles/feature.css';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import ReactMarkdown from 'react-markdown';

function ResourceRecommendation() {
  const [inputText, setInputText] = useState('');
  const [notesText, setNotesText] = useState('');
  const [newMessage, setNewMessage] = useState('');
  const [conversation, setConversation] = useState([]);
  const [submitted, setSubmitted] = useState(false);
  const [activeTab, setActiveTab] = useState('wellnessgoals');
  const [wellnessgoals, setwellnessgoals] = useState([]);
  const [chatConvo, setchatConvo] = useState([]);
  const latestMessageRef = useRef(newMessage);
  
  const handleInputChange = (e) => {
    setInputText(e.target.value);
  };

  const handleNotesChange = (e) => {
    setNotesText(e.target.value);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSave = () => {
    const blob = new Blob([notesText], { type: 'text/plain' });
    
    // Create a URL for the Blob
    const url = URL.createObjectURL(blob);
    
    // Create an anchor element and trigger a download
    const link = document.createElement('a');
    link.href = url;
    link.download = 'saved_notes.txt'; // Name of the file to be downloaded
    link.click();
    
    // Clean up the URL object
    URL.revokeObjectURL(url);
  };

  useEffect(() => {
    latestMessageRef.current = newMessage;
  }, [newMessage])

  const handleSubmit = async () => {
    if (inputText.trim()) {
      // Add user message to the conversation
      const new_message = "Client: "+inputText.trim()+", Notes: "+notesText.trim();
      const userMessage = { sender: 'user', text: inputText.trim()};
      setConversation((prev) => [...prev, userMessage]);
      setInputText('');
      setchatConvo((prev) => [...prev,{'role': 'user','content': inputText.trim()}])
      setNewMessage("");
      
      const botMessage = {
        sender: "bot",
        text: "Loading...", 
      };
      setConversation((prev) => [...prev, botMessage]);

      const baseUrl = `http://${window.location.hostname}:8000/wellness_response/`;

      await fetchEventSource(baseUrl, {
        method: "POST",
        headers: { Accept: "text/event-stream",         
                  'Content-Type': 'application/json', },
        body: JSON.stringify({
          "text": new_message, 
          "previous_text": chatConvo
        }),
        onopen(res) {
          if (res.status >= 400 && res.status < 500 && res.status !== 429) {
            console.log("Client-side error ", res);
          }
        },
        onmessage(event) {
          setNewMessage((prev) => {
            const updatedMessage = prev + event.data.replaceAll("<br/>","\n");
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
        retryInterval: 100000,
      });
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
              <ReactMarkdown children={msg.text} />
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

      <div className="right-section">
        <div className="tab-content">
          <h2>Notes</h2>
          <textarea
              className="notes-bar"
              placeholder={
                'Any notes during conversation'
              }
              value={notesText}
              onChange={handleNotesChange}
              rows={100}
            />  
        </div>
        <div class="notes-box">
          <button className="voice-icon">🎤</button>
          <button className="submit-button" onClick={handleSave}>💾</button>
        </div>
      </div>
    </div>
  );
}

export default ResourceRecommendation;
