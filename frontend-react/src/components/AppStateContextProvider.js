import React, { createContext, useState, useRef } from 'react';

// Create Context
export const WellnessContext = createContext();

// AppStateContext Provider
export const WellnessContextProvider = ({ children }) => {
  // Shared State
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [notesText, setNotesText] = useState('');
  const [inputText, setInputText] = useState('');
  const [modelSelect, setModel] = useState('copilot');
  const [newMessage, setNewMessage] = useState('');
  const [conversation, setConversation] = useState([]);
  const [submitted, setSubmitted] = useState(false);
  const [activeTab, setActiveTab] = useState('wellnessgoals');
  const [wellnessgoals, setWellnessGoals] = useState([]);
  const [chatConvo, setChatConvo] = useState([]);

  const resetContext = () => {
    setIsRecording(false);
    setMediaRecorder(null);
    setNotesText('');
    setInputText('');
    setModel('copilot');
    setNewMessage('');
    setConversation([]);
    setSubmitted(false);
    setActiveTab('wellnessgoals');
    setWellnessGoals([]);
    setChatConvo([]);
  };

  // Provider Value
  const contextValue = {
    // State
    isRecording,
    setIsRecording,
    mediaRecorder,
    setMediaRecorder,
    notesText,
    setNotesText,
    inputText,
    setInputText,
    modelSelect,
    setModel,
    newMessage,
    setNewMessage,
    conversation,
    setConversation,
    submitted,
    setSubmitted,
    activeTab,
    setActiveTab,
    wellnessgoals,
    setWellnessGoals,
    chatConvo,
    setChatConvo,
    resetContext
  };

  return (
    <WellnessContext.Provider value={contextValue}>
      {children}
    </WellnessContext.Provider>
  );
};


// Create Context
export const BenefitContext = createContext();

// AppStateContext Provider
export const BenefitContextProvider = ({ children }) => {
  // Shared State
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [notesText, setNotesText] = useState('');
  const [inputText, setInputText] = useState('');
  const [modelSelect,setModel] = useState('copilot'); 
  const [newMessage, setNewMessage] = useState('');
  const [conversation, setConversation] = useState([]);
  const [submitted, setSubmitted] = useState(false);
  const [activeTab, setActiveTab] = useState('wellnessgoals');
  const [benefits, setbenefits] = useState([]);
  const [chatConvo, setchatConvo] = useState([]);

  const resetContext = () => {
    setIsRecording(false);
    setMediaRecorder(null);
    setNotesText('');
    setInputText('');
    setModel('copilot');
    setNewMessage('');
    setConversation([]);
    setSubmitted(false);
    setActiveTab('wellnessgoals');
    setbenefits([]);
    setchatConvo([]);
  };

  // Provider Value
  const contextValue = {
    // State Variables
    isRecording,
    setIsRecording,
    mediaRecorder,
    setMediaRecorder,
    notesText,
    setNotesText,
    inputText,
    setInputText,
    modelSelect,
    setModel,
    newMessage,
    setNewMessage,
    conversation,
    setConversation,
    submitted,
    setSubmitted,
    activeTab,
    setActiveTab,
    benefits,
    setbenefits,
    chatConvo,
    setchatConvo,
    resetContext
  };

  return (
    <BenefitContext.Provider value={contextValue}>
      {children}
    </BenefitContext.Provider>
  );
};



// Create Context
export const ResourceContext = createContext();

// AppStateContext Provider
export const ResourceContextProvider = ({ children }) => {
  // Shared State
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [notesText, setNotesText] = useState('');
  const [inputText, setInputText] = useState('');
  const [modelSelect,setModel] = useState('copilot'); 
  const [inputLocationText, setInputLocationText] = useState('');
  const [newMessage, setNewMessage] = useState('');
  const [conversation, setConversation] = useState([]);
  const [submitted, setSubmitted] = useState(false);
  const [activeTab, setActiveTab] = useState('wellnessgoals');
  const [resources, setResources] = useState([]);
  const [chatConvo, setchatConvo] = useState([]);
  const latestMessageRef = useRef(newMessage);

  const resetContext = () => {
    setIsRecording(false);
    setMediaRecorder(null);
    setNotesText('');
    setInputText('');
    setModel('copilot');
    setInputLocationText('');
    setNewMessage('');
    setConversation([]);
    setSubmitted(false);
    setActiveTab('wellnessgoals');
    setResources([]);
    setchatConvo([]);
  };

  // Provider Value
  const contextValue = {
    // State Variables
    isRecording,
    setIsRecording,
    mediaRecorder,
    setMediaRecorder,
    notesText,
    setNotesText,
    inputText,
    setInputText,
    modelSelect,
    setModel,
    inputLocationText, 
    setInputLocationText,
    newMessage,
    setNewMessage,
    conversation,
    setConversation,
    submitted,
    setSubmitted,
    activeTab,
    setActiveTab,
    resources,
    setResources,
    chatConvo,
    setchatConvo,
    resetContext
  };

  return (
    <ResourceContext.Provider value={contextValue}>
      {children}
    </ResourceContext.Provider>
  );
};

