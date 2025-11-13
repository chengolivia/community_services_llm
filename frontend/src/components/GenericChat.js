import React, { useRef, useContext, useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';
import { jsPDF } from 'jspdf';
import io from 'socket.io-client';
import '../styles/feature.css';
import {WellnessContext } from './AppStateContextProvider';
import { API_URL } from '../config';


function GenericChat({ context, title, socketServerUrl, showLocation, tool }) {
  const {
    inputText, setInputText,
    inputLocationText, setInputLocationText,
    conversation, setConversation,
    submitted,
    chatConvo, setChatConvo,
    organization,setOrganization,
    user
  } = useContext(context);

  const inputRef = useRef(null);
  const conversationEndRef = useRef(null);
  const [socket, setSocket] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [autoScrollEnabled, setAutoScrollEnabled] = useState(true);
  const [conversationID, setConversationID] = useState("");
  const [goalsList, setGoalsList] = useState([]);
  const [resourcesList, setResourcesList] = useState([]);
  const [serviceUsers, setServiceUsers] = useState([]);
  const [selectedServiceUser, setSelectedServiceUser] = useState(''); // '' for general, or user ID
  const [pendingServiceUser, setPendingServiceUser] = useState(null);
  const [showResetWarning, setShowResetWarning] = useState(false);
  const [generatingCheckIns, setGeneratingCheckIns] = useState(false);
  const [checkIns, setCheckIns] = useState([]);

  useEffect(() => {
  if (!user?.username) {
    console.log('[Dropdown] No username available yet');
    return;
  }
  
  console.log('[Dropdown] Fetching service users for:', user.username);
  
  fetch(`${API_URL}/service_user_list/?name=${user.username}`)
    .then(res => {
      console.log('[Dropdown] Response status:', res.status);
      return res.json();
    })
    .then(data => {
      console.log('[Dropdown] Received data:', data);
      setServiceUsers(data);
    })
    .catch(error => {
      console.error('[Dropdown] Error:', error);
    });
}, [user?.username]);
  useEffect(() => {
    const newSocket = io(socketServerUrl, {
      transports: ['polling', 'websocket'],
      reconnectionAttempts: 5,
      timeout: 20000,
    });
    setSocket(newSocket);

    newSocket.on('connect', () => {
      console.log('[Socket.io] Connected to server');
    });

    newSocket.on("conversation_id", (data) => {
      setConversationID(data.conversation_id)
    }); 

    newSocket.on('welcome', (data) => {
      console.log('[Socket.io] Received welcome message:', data);
    });

    newSocket.on('generation_update', (data) => {
      console.log('[Socket.io] Received generation update:', data);
      if (typeof data.chunk === 'string') {
        setConversation(prev => {
          if (prev.length > 0 && prev[prev.length - 1].sender === 'bot') {
            const updated = [...prev];
            updated[updated.length - 1].text = data.chunk;
            return updated;
          }
          return [...prev, { sender: 'bot', text: data.chunk }];
        });
      }
      // setConversation((prev) => {
      //   if (prev.length > 0 && prev[prev.length - 1].sender === 'bot') {
      //     const updated = [...prev];
      //     updated[updated.length - 1].text = data.chunk;
      //     return updated;
      //   } else {
      //     return [...prev, { sender: 'bot', text: data.chunk }];
      //   }
      // });
    });

    newSocket.on('goals_update', ({ goals, resources }) => {
      console.log('[Socket.io] goals_update:', goals, resources);
      setGoalsList(goals);
      setResourcesList(resources);
    });

    newSocket.on('generation_complete', (data) => {
      console.log('[Socket.io] Generation complete:', data);
      setIsGenerating(false);
    });

    newSocket.on('error', (error) => {
      console.error('[Socket.io] Error:', error);
    });

    newSocket.on('disconnect', (reason) => {
      console.log('[Socket.io] Disconnected:', reason);
    });

    return () => {
      newSocket.disconnect();
    };
  }, [socketServerUrl]);

  useEffect(() => {
  fetch(`${API_URL}/service_user_list/?name=${user.username}`)  
    .then(res => res.json())
    .then(setServiceUsers)
    .catch(console.error);
}, [user.username]); 

  // Fetch check-ins when service user changes
  useEffect(() => {
    if (selectedServiceUser) {
      fetch(`${API_URL}/service_user_check_ins/?service_user_id=${selectedServiceUser}`)
        .then(res => res.json())
        .then(data => setCheckIns(data))
        .catch(error => {
          console.error('[Check-ins] Error fetching:', error);
          setCheckIns([]);
        });
    } else {
      setCheckIns([]);
    }
  }, [selectedServiceUser]);

  const handleScroll = (e) => {
    const { scrollTop, clientHeight, scrollHeight } = e.target;
    if (scrollTop + clientHeight >= scrollHeight - 50) {
      setAutoScrollEnabled(true);
    } else {
      setAutoScrollEnabled(false);
    }
  };
  
  useEffect(() => {
    if (autoScrollEnabled && conversationEndRef.current) {
      conversationEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [conversation, autoScrollEnabled]);
  

  const adjustTextareaHeight = (textarea) => {
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${textarea.scrollHeight}px`;
    }
  };

  useEffect(() => {
    if (inputRef.current) {
      adjustTextareaHeight(inputRef.current);
    }
  }, [inputText]);

  const handleInputChange = (e) => {
    setInputText(e.target.value);
    adjustTextareaHeight(e.target);
  };

  const handleInputChangeLocation = (e) => {
    setInputLocationText(e.target.value);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    if (!inputText.trim() || isGenerating) return;

    const messageText = inputText.trim();

    const userMsg = { sender: 'user', text: inputText.trim() };
    setConversation((prev) => [...prev, userMsg]);
    setChatConvo((prev) => [...prev, { role: 'user', content: inputText.trim() }]);
    setInputText('');

    setConversation((prev) => [...prev, { sender: 'bot', text: "Loading..." }]);
    setIsGenerating(true);

    if (socket) {
      console.log('[GenericChat] Emitting start_generation event');
      console.log(user.username);
      socket.emit('start_generation', {
        text: messageText,
        previous_text: chatConvo,
        model: "A",
        organization: organization, 
        tool,
        conversation_id: conversationID,
        username: user.username,
        service_user_id: selectedServiceUser || null,
      });
    } else {
      console.error('[GenericChat] Socket is not connected.');
    }
  };
  
  const handleNewSession = () => {
    window.location.reload();
  };

  const exportChatToPDF = () => {
    const doc = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4',
    });
    doc.setFontSize(16);
    doc.text('Chat History', 10, 10);

    let yPosition = 20;
    const lineHeight = 10;
    const pageHeight = doc.internal.pageSize.height;

    conversation.forEach((msg) => {
      const sender = msg.sender === 'user' ? 'You' : 'Bot';
      const text = `${sender}: ${msg.text}`;
      const lines = doc.splitTextToSize(text, 180);
      lines.forEach((line) => {
        if (yPosition + lineHeight > pageHeight - 10) {
          doc.addPage();
          yPosition = 10;
        }
        doc.text(line, 10, yPosition);
        yPosition += lineHeight;
      });
    });

    doc.save('Chat_History.pdf');
  };

  const handleServiceUserChange = (e) => {
    const newUserId = e.target.value; // '' for general, or actual user ID
    
    // If there's an active conversation, show warning before switching
    if (chatConvo.length > 0 && selectedServiceUser !== newUserId) {
      setPendingServiceUser(newUserId);
      setShowResetWarning(true);
    } else {
      // No conversation yet, just switch
      setSelectedServiceUser(newUserId);
    }
  };

  // Confirm the switch and reset
  const confirmServiceUserSwitch = () => {
    setConversation([]);   
    setChatConvo([]);
    setConversationID('');
    
    setGoalsList([]);       
    setResourcesList([]);   
    
    // Emit reset to backend
    if (socket) {
      socket.emit('reset_session', { 
        reason: 'service_user_switch',
        previous_service_user_id: selectedServiceUser || 'general',
        new_service_user_id: pendingServiceUser || 'general'
      });
    }
    
    // Switch to new selection
    setSelectedServiceUser(pendingServiceUser);
    setPendingServiceUser(null);
    setShowResetWarning(false);
    
    console.log('[Chat] Switched service user context, chat reset');
  };

  // Cancel the switch
  const cancelServiceUserSwitch = () => {
    setPendingServiceUser(null);
    setShowResetWarning(false);
  };

  const handleGenerateCheckIns = async () => {
    if (!selectedServiceUser) {
      alert("Please select a service user first");
      return;
    }
    
    setGeneratingCheckIns(true);
    try {
      const response = await fetch(`${API_URL}/generate_check_ins/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ service_user_id: selectedServiceUser, 
          conversation_id: conversationID,
         })
      });
      
      const data = await response.json();
      if (data.success) {
        alert(`Generated ${data.check_ins.length} check-ins successfully!`);
        // Refresh check-ins
        const refreshResponse = await fetch(`${API_URL}/service_user_check_ins/?service_user_id=${selectedServiceUser}`);
        const refreshedCheckIns = await refreshResponse.json();
        setCheckIns(refreshedCheckIns);
      }
    } catch (error) {
      console.error('Error generating check-ins:', error);
      alert('Failed to generate check-ins');
    } finally {
      setGeneratingCheckIns(false);
    }
  };

  return (
    <div className="resource-recommendation-container">
      <div className="content-area">
        <div className={`left-section ${submitted ? 'submitted' : ''}`}>
          <h1 className="page-title">{title}</h1>
          <select 
              value={selectedServiceUser} 
              onChange={handleServiceUserChange}
          >
              <option value="">General Inquiry (not user-specific)</option>
              <optgroup label="Service Users">
                {serviceUsers.map(user => (
                  <option key={user.service_user_id} value={user.service_user_id}>
                    {user.service_user_name}
                  </option>
                ))}
              </optgroup>
          </select>
          <button
            className="submit-button"
            style={{ 
              width: 'auto', 
              padding: '8px 16px',
              fontSize: '14px',
              whiteSpace: 'nowrap'
            }}
            onClick={handleGenerateCheckIns}
            disabled={!selectedServiceUser || generatingCheckIns}
          >
            {generatingCheckIns ? 'Generating...' : 'Generate Check-ins'}
          </button>
          <h2 className="instruction">
            What is the service user’s needs and goals for today’s meeting?
          </h2>
          <div 
            className={`conversation-thread ${submitted ? 'visible' : ''}`}
            onScroll={handleScroll}
            style={{ overflowY: 'auto', maxHeight: '80vh' }} // ensure the container is scrollable
          >
            {conversation.map((msg, index) => (
              <div key={index} className={`message-blurb ${msg.sender === 'user' ? 'user' : 'bot'}`}>
                <ReactMarkdown
                  children={msg.text}
                  skipHtml={false}
                  rehypePlugins={[rehypeRaw]}
                  components={{
                    a: ({ href, children }) => (
                      <a href={href} target="_blank" rel="noopener noreferrer">
                        {children}
                      </a>
                    ),
                  }}
                />
              </div>
            ))}
            <div ref={conversationEndRef} />
          </div>
          </div>
          {/* ← NEW: Right‐hand panel containing two empty boxes */}
        <div className="right-section">
        {/* Goals panel */}
        <div className="goals-box" style={{ height: '400px' }}>
          <h3>Goals</h3>
          <div className="scroll-container">
            {goalsList.map((goal, idx) => (
              <div key={idx} className="resource-item">
                <ReactMarkdown
                  children={goal}
                  skipHtml={false}
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeRaw]}
                  components={{
                    a: ({ href, children }) => (
                      <a href={href} target="_blank" rel="noopener noreferrer">
                        {children}
                      </a>
                    ),
                  }}
                />
              </div>
            ))}
          </div>
        </div>

          {/* Resources panel */}
          <div className="resources-box" style={{ height: '500px' }}>
            <h3>Resources</h3>
            <div className="scroll-container">
              {resourcesList.map((res, idx) => {
                // Parse the backend’s flat “Name — [Link](url) (Action: act)” string
                // into a pretty markdown with name bold, link & action on their own lines.
                const regex = /^(.*?)\s+—\s+\[Link\]\((.*?)\)\s*(?:\(Action:\s*(.*?)\))?$/;
                const match = res.match(regex);
                let mdString = res;
                if (match) {
                  const [, name, linkUrl, action] = match;
                  mdString =
                    `**${name}**  \n` +     // bold name + linebreak
                    `[Link](${linkUrl})  \n` + // link + linebreak
                    `**Action:** ${action}`;   // action
                }

                return (
                  <div key={idx} className="resource-item">
                    <ReactMarkdown
                      children={mdString}
                      skipHtml={false}
                      remarkPlugins={[remarkGfm]}
                      rehypePlugins={[rehypeRaw]}
                      components={{
                        a: ({ href, children }) => (
                          <a href={href} target="_blank" rel="noopener noreferrer">
                            {children}
                          </a>
                        ),
                      }}
                    />
                  </div>
                );
              })}
            </div>
          </div>
        </div> 
      </div>
      <div className={`input-section ${submitted ? 'input-bottom' : ''}`}>
        {showLocation && (
          <div className="input-box">
            <textarea
              className="input-bar"
              placeholder="Enter location (city or county)"
              value={inputLocationText}
              onChange={handleInputChangeLocation}
              rows={1}
            />
          </div>
        )}
        <div className="input-box">
          <textarea
            className="input-bar"
            ref={inputRef}
            placeholder={
              submitted
                ? 'Write a follow-up to update...'
                : 'Describe the service user’s situation...'
            }
            value={inputText}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            rows={1}
            style={{ overflow: 'hidden', resize: 'none' }}
          />
          <button className="submit-button" onClick={handleSubmit}>
            ➤
          </button>
        </div>
              {showResetWarning && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3>Switch Context?</h3>
            <p>
              {pendingServiceUser ? (
                <>Switching to <strong>{serviceUsers.find(u => u.service_user_id === pendingServiceUser)?.service_user_name}</strong> will clear the current conversation.</>
              ) : (
                <>Switching to <strong>General Inquiry</strong> will clear the current conversation.</>
              )}
            </p>
            <p>This action cannot be undone.</p>
            <div className="modal-buttons">
              <button 
                onClick={cancelServiceUserSwitch}
                className="btn-cancel"
              >
                Cancel
              </button>
              <button 
                onClick={confirmServiceUserSwitch}
                className="btn-confirm"
              >
                Switch & Reset Chat
              </button>
            </div>
          </div>
        </div>
      )}
        <div className="backend-selector-div">
          <button
            className="submit-button"
            style={{ width: '60px', height: '100%', marginLeft: '20px' }}
            onClick={handleNewSession}
          >
            Reset Session
          </button>
          <button
            className="submit-button"
            style={{ width: '60px', height: '100%', marginLeft: '20px' }}
            onClick={exportChatToPDF}
          >
            Save Session History
          </button>
          {tool === "wellness" && (
            <button
              className="submit-button"
              style={{ width: '60px', height: '100%', marginLeft: '20px' }}
              onClick={() => window.open('https://www.youtube.com/watch?v=4rg1wmo2Y8w', '_blank')}
            >
              Tutorial
            </button>
          )}
        </div>
        </div>
    </div>
  );
}

export const WellnessGoals = () => (
  <GenericChat
    context={WellnessContext}
    title="Wellness Goals"
    socketServerUrl={`${API_URL}`}
    showLocation={false}
    tool="wellness"
  />
);

export default GenericChat;
