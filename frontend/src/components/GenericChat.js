import React, { useRef, useContext, useEffect, useState, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';
import { jsPDF } from 'jspdf';
import io from 'socket.io-client';
import '../styles/components/chat.css';
import { WellnessContext } from './AppStateContextProvider';
import { apiGet } from '../utils/api';
import { API_URL } from '../config';

// Constants
const SOCKET_CONFIG = {
  transports: ['polling', 'websocket'],
  reconnectionAttempts: 5,
  timeout: 20000,
};

const PDF_CONFIG = {
  orientation: 'portrait',
  unit: 'mm',
  format: 'a4',
  lineHeight: 10,
  margin: 10,
};

const SCROLL_THRESHOLD = 50;

// Extracted Components
const MarkdownContent = ({ content }) => (
  <ReactMarkdown
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
  >
    {content}
  </ReactMarkdown>
);

const ServiceUserSelector = ({ serviceUsers, selectedServiceUser, onChange }) => (
  <select value={selectedServiceUser} onChange={onChange}>
    <option value="">General Inquiry (not user-specific)</option>
    <optgroup label="Service Users">
      {serviceUsers.map(user => (
        <option key={user.service_user_id} value={user.service_user_id}>
          {user.service_user_name}
        </option>
      ))}
    </optgroup>
  </select>
);

const ResetWarningModal = ({ pendingServiceUser, serviceUsers, onConfirm, onCancel }) => {
  const getUserName = () => {
    if (!pendingServiceUser) return 'General Inquiry';
    return serviceUsers.find(u => u.service_user_id === pendingServiceUser)?.service_user_name;
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h3>Switch Context?</h3>
        <p>
          Switching to <strong>{getUserName()}</strong> will clear the current conversation.
        </p>
        <p>This action cannot be undone.</p>
        <div className="modal-buttons">
          <button onClick={onCancel} className="btn-cancel">
            Cancel
          </button>
          <button onClick={onConfirm} className="btn-confirm">
            Switch & Reset Chat
          </button>
        </div>
      </div>
    </div>
  );
};

const ResourceItem = ({ content, className = '' }) => {
  // Parse resource format: "Name — [Link](url) (Action: act)"
  const parseResource = (text) => {
    const regex = /^(.*?)\s+—\s+\[Link\]\((.*?)\)\s*(?:\(Action:\s*(.*?)\))?$/;
    const match = text.match(regex);
    
    if (match) {
      const [, name, linkUrl, action] = match;
      return `**${name}**  \n[Link](${linkUrl})  \n**Action:** ${action}`;
    }
    return text;
  };

  const shouldShowTopBorder = (text) => {
    const firstWord = text.trim().split(/\s+/)[0].replace(/[*_#>-]/g, '');
    return ['Goal', 'Resource'].includes(firstWord);
  };

  const showBorder = shouldShowTopBorder(content);
  const parsedContent = parseResource(content);

  return (
    <div className={`resource-item ${showBorder ? 'with-top-border' : ''} ${className}`}>
      <MarkdownContent content={parsedContent} />
    </div>
  );
};

function GenericChat({ context, title, socketServerUrl, showLocation, tool }) {
  const {
    inputText,
    setInputText,
    inputLocationText,
    setInputLocationText,
    conversation,
    setConversation,
    chatConvo,
    setChatConvo,
    organization,
    user,
  } = useContext(context);

  const inputRef = useRef(null);
  const conversationEndRef = useRef(null);
  
  const [socket, setSocket] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [autoScrollEnabled, setAutoScrollEnabled] = useState(true);
  const [conversationID, setConversationID] = useState('');
  const [goalsList, setGoalsList] = useState([]);
  const [resourcesList, setResourcesList] = useState([]);
  const [serviceUsers, setServiceUsers] = useState([]);
  const [selectedServiceUser, setSelectedServiceUser] = useState('');
  const [pendingServiceUser, setPendingServiceUser] = useState(null);
  const [showResetWarning, setShowResetWarning] = useState(false);

  // Fetch service users
  useEffect(() => {
    const fetchServiceUsers = async () => {
      if (!user?.username) return;
      
      try {
        console.log('[Dropdown] Fetching service users...');
        const data = await apiGet(`/service_user_list/?name=${user.username}`);
        console.log('[Dropdown] Received data:', data);
        setServiceUsers(data);
      } catch (error) {
        console.error('[Dropdown] Error:', error);
      }
    };

    fetchServiceUsers();
  }, [user?.username]);

  // Socket setup
  useEffect(() => {
    const newSocket = io(socketServerUrl, SOCKET_CONFIG);
    setSocket(newSocket);

    newSocket.on('connect', () => {
      console.log('[Socket.io] Connected to server');
    });

    newSocket.on('conversation_id', (data) => {
      setConversationID(data.conversation_id);
    });

    newSocket.on('welcome', (data) => {
      console.log('[Socket.io] Received welcome message:', data);
    });

    newSocket.on('generation_update', (data) => {
      console.log('[Socket.io] Received generation update:', data);
      if (typeof data.chunk === 'string') {
        setConversation(prev => {
          const lastMessage = prev[prev.length - 1];
          if (lastMessage?.sender === 'bot') {
            const updated = [...prev];
            updated[updated.length - 1].text = data.chunk;
            return updated;
          }
          return [...prev, { sender: 'bot', text: data.chunk }];
        });
      }
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
  }, [socketServerUrl, setConversation]);

  // Auto-scroll management
  const handleScroll = useCallback((e) => {
    const { scrollTop, clientHeight, scrollHeight } = e.target;
    setAutoScrollEnabled(scrollTop + clientHeight >= scrollHeight - SCROLL_THRESHOLD);
  }, []);

  useEffect(() => {
    if (autoScrollEnabled && conversationEndRef.current) {
      conversationEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [conversation, autoScrollEnabled]);

  // Textarea auto-resize
  const adjustTextareaHeight = useCallback((textarea) => {
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${textarea.scrollHeight}px`;
    }
  }, []);

  useEffect(() => {
    adjustTextareaHeight(inputRef.current);
  }, [inputText, adjustTextareaHeight]);

  // Input handlers
  const handleInputChange = useCallback((e) => {
    setInputText(e.target.value);
    adjustTextareaHeight(e.target);
  }, [setInputText, adjustTextareaHeight]);

  const handleInputChangeLocation = useCallback((e) => {
    setInputLocationText(e.target.value);
  }, [setInputLocationText]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }, [inputText, isGenerating, socket, chatConvo, conversationID, organization, user, tool]);

  const handleSubmit = useCallback(() => {
    if (!inputText.trim() || isGenerating || !socket) return;

    const messageText = inputText.trim();
    const userMsg = { sender: 'user', text: messageText };

    setConversation(prev => [...prev, userMsg, { sender: 'bot', text: 'Loading...' }]);
    setChatConvo(prev => [...prev, { role: 'user', content: messageText }]);
    setInputText('');
    setIsGenerating(true);

    console.log('[GenericChat] Emitting start_generation event');
    socket.emit('start_generation', {
      text: messageText,
      previous_text: chatConvo,
      model: 'A',
      organization,
      tool,
      conversation_id: conversationID,
      username: user.username,
      service_user_id: user.service_user_id || null,
    });
  }, [
    inputText,
    isGenerating,
    socket,
    chatConvo,
    conversationID,
    organization,
    user,
    tool,
    setConversation,
    setChatConvo,
    setInputText,
  ]);

  // Session management
  const handleNewSession = useCallback(() => {
    window.location.reload();
  }, []);

  const exportChatToPDF = useCallback(() => {
    const doc = new jsPDF(PDF_CONFIG);
    doc.setFontSize(16);
    doc.text('Chat History', PDF_CONFIG.margin, PDF_CONFIG.margin);

    let yPosition = 20;
    const pageHeight = doc.internal.pageSize.height;

    conversation.forEach((msg) => {
      const sender = msg.sender === 'user' ? 'You' : 'Bot';
      const text = `${sender}: ${msg.text}`;
      const lines = doc.splitTextToSize(text, 180);
      
      lines.forEach((line) => {
        if (yPosition + PDF_CONFIG.lineHeight > pageHeight - PDF_CONFIG.margin) {
          doc.addPage();
          yPosition = PDF_CONFIG.margin;
        }
        doc.text(line, PDF_CONFIG.margin, yPosition);
        yPosition += PDF_CONFIG.lineHeight;
      });
    });

    doc.save('Chat_History.pdf');
  }, [conversation]);

  // Service user switching
  const handleServiceUserChange = useCallback((e) => {
    const newUserId = e.target.value;
    
    if (chatConvo.length > 0 && selectedServiceUser !== newUserId) {
      setPendingServiceUser(newUserId);
      setShowResetWarning(true);
    } else {
      setSelectedServiceUser(newUserId);
    }
  }, [chatConvo.length, selectedServiceUser]);

  const confirmServiceUserSwitch = useCallback(() => {
    setConversation([]);
    setChatConvo([]);
    setConversationID('');
    setGoalsList([]);
    setResourcesList([]);

    if (socket) {
      socket.emit('reset_session', {
        reason: 'service_user_switch',
        previous_service_user_id: selectedServiceUser || 'general',
        new_service_user_id: pendingServiceUser || 'general',
      });
    }

    setSelectedServiceUser(pendingServiceUser);
    setPendingServiceUser(null);
    setShowResetWarning(false);
    console.log('[Chat] Switched service user context, chat reset');
  }, [socket, selectedServiceUser, pendingServiceUser, setConversation, setChatConvo]);

  const cancelServiceUserSwitch = useCallback(() => {
    setPendingServiceUser(null);
    setShowResetWarning(false);
  }, []);

  const submitted = conversation.length > 0;

  return (
    <div className="resource-recommendation-container">
      <div className="content-area">
        <div className={`left-section ${submitted ? 'submitted' : ''}`}>
          <h1 className="page-title">{title}</h1>
          
          <ServiceUserSelector
            serviceUsers={serviceUsers}
            selectedServiceUser={selectedServiceUser}
            onChange={handleServiceUserChange}
          />
          
          <h2 className="instruction">
            What is the service user's needs and goals for today's meeting?
          </h2>
          
          <div
            className={`conversation-thread ${submitted ? 'visible' : ''}`}
            onScroll={handleScroll}
            style={{ overflowY: 'auto', maxHeight: '80vh' }}
          >
            {conversation.map((msg, index) => (
              <div key={index} className={`message-blurb ${msg.sender}`}>
                <MarkdownContent content={msg.text} />
              </div>
            ))}
            <div ref={conversationEndRef} />
          </div>
        </div>

        <div className="right-section">
          <div className="goals-box">
            <h3>Goals</h3>
            <div className="scroll-container">
              {goalsList.map((goal, idx) => (
                <ResourceItem key={`goal-${idx}`} content={goal} />
              ))}
            </div>
          </div>

          <div className="resources-box">
            <h3>Resources</h3>
            <div className="scroll-container">
              {resourcesList.map((res, idx) => (
                <ResourceItem key={`resource-${idx}`} content={res} />
              ))}
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
                : "Describe the service user's situation..."
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
          <ResetWarningModal
            pendingServiceUser={pendingServiceUser}
            serviceUsers={serviceUsers}
            onConfirm={confirmServiceUserSwitch}
            onCancel={cancelServiceUserSwitch}
          />
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
          {tool === 'wellness' && (
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