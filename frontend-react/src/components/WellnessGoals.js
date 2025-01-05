import React, { useRef, useContext } from 'react';
import '../styles/feature.css';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import ReactMarkdown from 'react-markdown';
import {WellnessContext} from './AppStateContextProvider.js';

function WellnessGoals() {
  const {
    inputText, setInputText,
    modelSelect, setModel,
    inputLocationText, setInputLocationText,
    newMessage, setNewMessage,
    conversation, setConversation,
    submitted,
    chatConvo, setChatConvo, 
    resetContext
  } = useContext(WellnessContext);
  const latestMessageRef = useRef(newMessage);

  const handleInputChange = (e) => {
    setInputText(e.target.value);
  };

  const handleModelChange = (e) => {
    setModel(e.target.value);
  };


  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault(); // Prevent new line
      handleSubmit(); // Submit input
    }
  };

  const handleNewSession = async () => {
    resetContext();
  }


  const handleSubmit = async () => {
    if (inputText.trim()) {
      // Add user message to the conversation
      const new_message = inputText.trim();
      const userMessage = { sender: 'user', text: inputText.trim()};
      setConversation((prev) => [...prev, userMessage]);
      setInputText('');
      setChatConvo((prev) => [...prev,{'role': 'user','content': inputText.trim()}])
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
          "previous_text": chatConvo, 
          "model": modelSelect, 
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
          setChatConvo((prev) => [...prev,{'role': 'system','content': latestMessageRef.current}])
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
              <button className="submit-button" onClick={handleSubmit}>
                ➤
              </button>
            </div>
            <div className="backend-selector-div"> 
              <select onChange={handleModelChange} value={modelSelect} name="model" id="model" className="backend-select">
                  <option value="copilot">Co-Pilot</option>
                  <option value="chatgpt">ChatGPT</option>
                </select>
              
              <button className="submit-button" style={{width: '100px', 'height': '100%', 'marginLeft': '20px'}} onClick={handleNewSession}>
                Reset Session
              </button>

            </div> 
          </div>
        </div>
      </div>
  );
}

export default WellnessGoals;
