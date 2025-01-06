import React, { useRef, useContext } from 'react';
import '../styles/feature.css';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import ReactMarkdown from 'react-markdown';
import {BenefitContext,ResourceContext,WellnessContext} from './AppStateContextProvider.js';

function GenericChat({ context, title, baseUrl,showLocation }) {
  const {
    inputText, setInputText,
    modelSelect, setModel,
    inputLocationText, setInputLocationText,
    newMessage, setNewMessage,
    conversation, setConversation,
    submitted,
    chatConvo, setChatConvo,
    resetContext
  } = useContext(context);

  const latestMessageRef = useRef(newMessage);

  const handleInputChange = (e) => setInputText(e.target.value);
  const handleModelChange = (e) => setModel(e.target.value);
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInputChangeLocation = (e) => setInputLocationText(e.target.value);
  const handleNewSession = async () => resetContext();
  let shouldFetch = true;  // Set to true initially or based on your logic

  let abortController = new AbortController();  // Initialize a new controller
  let isRequestInProgress = false;  // Track if a request is already in progress
  
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden' && isRequestInProgress) {
      // Abort the current request when the tab becomes hidden
      abortController.abort();
      isRequestInProgress = false;
    }
  });
  

  const handleSubmit = async () => {
    if (inputText.trim() && shouldFetch && !isRequestInProgress) {
      const newMessage = inputText.trim() + "\n Location: " + (inputLocationText.trim() || "New Jersey");
      const userMessage = { sender: 'user', text: inputText.trim() };
      setConversation((prev) => [...prev, userMessage]);
      setInputText('');
      setChatConvo((prev) => [...prev, { 'role': 'user', 'content': inputText.trim() }]);
      setNewMessage("");

      const botMessage = { sender: "bot", text: "Loading..." };
      setConversation((prev) => [...prev, botMessage]);
      shouldFetch = false;

      abortController.abort();
      abortController = new AbortController(); // Create a new controller for the new request
      isRequestInProgress = true;  

      await fetchEventSource(baseUrl, {
        method: "POST",
        headers: { Accept: "text/event-stream", 'Content-Type': 'application/json' },
        signal: abortController.signal,
        body: JSON.stringify({ "text": newMessage, "previous_text": chatConvo, "model": modelSelect }),
        onopen(res) {
          if (res.status >= 400 && res.status < 500 && res.status !== 429) {
            console.log("Client-side error ", res);
          }
        },
        onmessage(event) {
          setNewMessage((prev) => {
            const updatedMessage = prev + event.data.replaceAll("<br/>", "\n");
            const botMessage = { sender: "bot", text: updatedMessage };
            setConversation((convPrev) => {
              if (convPrev.length > 0) {
                return [...convPrev.slice(0, -1), botMessage];
              }
              return [botMessage];
            });
            return updatedMessage;
          });
        },
        onclose() {
          setChatConvo((prev) => [...prev, { 'role': 'system', 'content': latestMessageRef.current }]);
          shouldFetch = true;
        },
        onerror(err) {
          shouldFetch = true;
          console.log("There was an error from server", err);
        },
        retryInterval: 0
      });
    }
  };

  return (
    <div className="resource-recommendation-container">
      <div className={`left-section ${submitted ? 'submitted' : ''}`}>
        <h1 className="page-title">{title}</h1>
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
          {showLocation && <div className="input-box">
            <textarea
              className="input-bar"
              placeholder={'Enter location (city or county)'}
              value={inputLocationText}
              onChange={handleInputChangeLocation}
              rows={1}
            />
          </div>}
          <div className="input-box">
            <textarea
              className="input-bar"
              placeholder={submitted ? 'Write a follow-up to update...' : 'Describe your client’s situation...'}
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
            <button className="submit-button" style={{ width: '100px', height: '100%', marginLeft: '20px' }} onClick={handleNewSession}>
              Reset Session
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}



export const ResourceRecommendation = () => (
  <GenericChat context={ResourceContext} title="Resource Database" baseUrl={`http://${window.location.hostname}:8000/resource_response/`} showLocation={true} />
);

export const WellnessGoals = () => (
  <GenericChat context={WellnessContext} title="Wellness Goals" baseUrl={`http://${window.location.hostname}:8000/wellness_response/`} showLocation={false} />
);

export const BenefitEligibility = () => (
  <GenericChat context={BenefitContext} title="Benefit Eligibility" baseUrl={`http://${window.location.hostname}:8000/benefit_response/`} showLocation={false} />
);

export default GenericChat;
