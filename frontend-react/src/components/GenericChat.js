// import React, { useRef, useContext, useEffect, useState } from 'react';
// import '../styles/feature.css';
// import { fetchEventSource } from '@microsoft/fetch-event-source';
// import ReactMarkdown from 'react-markdown';
// import { jsPDF } from 'jspdf';
// import { BenefitContext, ResourceContext, WellnessContext } from './AppStateContextProvider.js';

// function GenericChat({ context, title, baseUrl, showLocation }) {
//   const {
//     inputText, setInputText,
//     modelSelect, setModel,
//     inputLocationText, setInputLocationText,
//     newMessage, setNewMessage,
//     conversation, setConversation,
//     submitted,
//     chatConvo, setChatConvo,
//     resetContext
//   } = useContext(context);

//   const inputRef = useRef(null); // For dynamic textarea height
//   const conversationEndRef = useRef(null);

//   // Refs to persist connection state between renders.
//   const abortControllerRef = useRef(new AbortController());
//   const isRequestInProgressRef = useRef(false);
//   const pendingMessageRef = useRef(""); // Stores the message that started the fetch

//   const [isResponseComplete, setIsResponseComplete] = useState(true); // true when the bot response finished
//   // No longer need an explicit “midGeneration” flag—if the response isn’t complete, we assume we can resume

//   const handleInputChange = (e) => {
//     setInputText(e.target.value);
//     adjustTextareaHeight(e.target);
//   };

//   const handleModelChange = (e) => setModel(e.target.value);

//   const handleKeyDown = (e) => {
//     if (e.key === 'Enter' && !e.shiftKey) {
//       e.preventDefault();
//       handleSubmit();
//     }
//   };

//   // NEW: onerror callback and a simplified resumeFetch that always tries to reconnect if response is incomplete.
//   const resumeFetch = async () => {
//     // Only resume if we haven't finished the response and no request is in progress.
//     if (isResponseComplete || isRequestInProgressRef.current) return;

//     // (Re)initialize the abort controller.
//     abortControllerRef.current = new AbortController();
//     isRequestInProgressRef.current = true;
    
//     // Clear any leftover message content.
//     setNewMessage('');
//     // Use the stored pending message.
//     const pendingMessage = pendingMessageRef.current;
//     const botMessage = { sender: "bot", text: "Loading..." };
//     setConversation((prev) => [...prev, botMessage]);

//     try {
//       await fetchEventSource(baseUrl, {
//         method: "POST",
//         headers: { 
//           Accept: "text/event-stream", 
//           "Content-Type": "application/json" 
//         },
//         signal: abortControllerRef.current.signal,
//         body: JSON.stringify({
//           text: pendingMessage,
//           previous_text: chatConvo,
//           model: modelSelect
//         }),
//         onmessage(event) {
//           setNewMessage((prev) => {
//             const updatedMessage = prev + event.data.replaceAll("<br/>", "\n");
//             const botMsg = { sender: "bot", text: updatedMessage };
//             setConversation((convPrev) => {
//               if (convPrev.length > 0) {
//                 return [...convPrev.slice(0, -1), botMsg];
//               }
//               return [botMsg];
//             });
//             return updatedMessage;
//           });
//         },
//         onerror(err) {
//           console.error("SSE onerror in resumeFetch:", err);
//           isRequestInProgressRef.current = false;
//           // Retry after a short delay if the response is still not complete.
//           if (!isResponseComplete && document.visibilityState === 'visible') {
//             setTimeout(() => {
//               resumeFetch();
//             }, 1000);
//           }
//         },
//         onclose() {
//           setIsResponseComplete(true);
//           isRequestInProgressRef.current = false;
//         },
//       });
//     } catch (err) {
//       console.error("Fetch failed in resumeFetch:", err);
//       isRequestInProgressRef.current = false;
//     }
//   };

//   const handleInputChangeLocation = (e) => setInputLocationText(e.target.value);

//   const handleNewSession = async () => {
//     // Abort any ongoing connection and reset state.
//     abortControllerRef.current.abort();
//     abortControllerRef.current = new AbortController();
//     resetContext();
//   };

//   const handleSubmit = async () => {
//     if (inputText.trim() && !isRequestInProgressRef.current) {
//       // (Re)initialize abort controller if needed.
//       if (abortControllerRef.current.signal.aborted) {
//         abortControllerRef.current = new AbortController();
//       }

//       // Build the message (including location) and store it for possible resume.
//       const newMessageText = inputText.trim() + "\n Location: " + (inputLocationText.trim() || "New Jersey");
//       pendingMessageRef.current = newMessageText;

//       const userMessage = { sender: 'user', text: inputText.trim() };
//       setConversation((prev) => [...prev, userMessage]);
//       setInputText('');
//       setChatConvo((prev) => [...prev, { role: 'user', content: inputText.trim() }]);
//       setNewMessage("");
//       setIsResponseComplete(false);

//       const botMessage = { sender: "bot", text: "Loading..." };
//       setConversation((prev) => [...prev, botMessage]);

//       isRequestInProgressRef.current = true;

//       try {
//         await fetchEventSource(baseUrl, {
//           method: "POST",
//           headers: { Accept: "text/event-stream", 'Content-Type': 'application/json' },
//           signal: abortControllerRef.current.signal,
//           body: JSON.stringify({ text: newMessageText, previous_text: chatConvo, model: modelSelect }),
//           onmessage(event) {
//             setNewMessage((prev) => {
//               const updatedMessage = prev + event.data.replaceAll("<br/>", "\n");
//               const botMsg = { sender: "bot", text: updatedMessage };
//               setConversation((convPrev) => {
//                 if (convPrev.length > 0) {
//                   return [...convPrev.slice(0, -1), botMsg];
//                 }
//                 return [botMsg];
//               });
//               return updatedMessage;
//             });
//           },
//           onerror(err) {
//             console.error("SSE onerror in handleSubmit:", err);
//             isRequestInProgressRef.current = false;
//             // On error, if the tab is visible and response incomplete, attempt to resume.
//             if (!isResponseComplete && document.visibilityState === 'visible') {
//               setTimeout(() => {
//                 resumeFetch();
//               }, 1000);
//             }
//           },
//           onclose() {
//             setIsResponseComplete(true);
//             isRequestInProgressRef.current = false;
//           },
//         });
//       } catch (err) {
//         console.error("Fetch failed in handleSubmit:", err);
//       } finally {
//         isRequestInProgressRef.current = false;
//       }
//     }
//   };

//   // Dynamically adjust the textarea height.
//   const adjustTextareaHeight = (textarea) => {
//     if (textarea) {
//       textarea.style.height = 'auto';
//       textarea.style.height = `${textarea.scrollHeight}px`;
//     }
//   };

//   // Visibility change handler:
//   useEffect(() => {
//     const handleVisibilityChange = () => {
//       if (document.visibilityState === 'visible') {
//         // When returning to the tab, if the response isn’t complete and no request is in progress,
//         // reinitialize the connection.
//         if (!isResponseComplete && !isRequestInProgressRef.current) {
//           // Abort any lingering connection (just in case) and start a new one.
//           abortControllerRef.current.abort();
//           abortControllerRef.current = new AbortController();
//           resumeFetch();
//         }
//       }
//       // On hidden, we no longer abort the connection so that any in‑progress stream can be resumed.
//     };

//     document.addEventListener('visibilitychange', handleVisibilityChange);
//     return () => {
//       document.removeEventListener('visibilitychange', handleVisibilityChange);
//     };
//   }, [isResponseComplete, chatConvo, modelSelect]);

//   // Adjust textarea height when inputText changes.
//   useEffect(() => {
//     if (inputRef.current) {
//       adjustTextareaHeight(inputRef.current);
//     }
//   }, [inputText]);

//   // Auto-scroll to the bottom whenever the conversation updates.
//   useEffect(() => {
//     if (conversationEndRef.current) {
//       setTimeout(() => {
//         conversationEndRef.current.scrollIntoView({ behavior: 'smooth' });
//       }, 100);
//     }
//   }, [conversation]);

//   // Export chat history as PDF.
//   const exportChatToPDF = () => {
//     const doc = new jsPDF({
//       orientation: 'portrait',
//       unit: 'mm',
//       format: 'a4',
//     });
//     doc.setFontSize(16);
//     doc.text('Chat History', 10, 10);

//     let yPosition = 20;
//     const lineHeight = 10;
//     const pageHeight = doc.internal.pageSize.height;

//     conversation.forEach((msg) => {
//       const sender = msg.sender === 'user' ? 'You' : 'Bot';
//       const text = `${sender}: ${msg.text}`;
//       const lines = doc.splitTextToSize(text, 180);
//       lines.forEach((line) => {
//         if (yPosition + lineHeight > pageHeight - 10) {
//           doc.addPage();
//           yPosition = 10;
//         }
//         doc.text(line, 10, yPosition);
//         yPosition += lineHeight;
//       });
//     });

//     doc.save('Chat_History.pdf');
//   };

//   return (
//     <div className="resource-recommendation-container">
//       <div className={`left-section ${submitted ? 'submitted' : ''}`}>
//         <h1 className="page-title">{title}</h1>
//         <h2 className="instruction">
//           What is the service user’s needs and goals for today’s meeting?
//         </h2>
//         <div className={`conversation-thread ${submitted ? 'visible' : ''}`}>
//           {conversation.map((msg, index) => (
//             <div
//               key={index}
//               className={`message-blurb ${msg.sender === 'user' ? 'user' : 'bot'}`}
//             >
//               <ReactMarkdown
//                 children={msg.text}
//                 components={{
//                   a: ({ href, children }) => (
//                     <a href={href} target="_blank" rel="noopener noreferrer">
//                       {children}
//                     </a>
//                   ),
//                 }}
//               />
//             </div>
//           ))}
//           <div ref={conversationEndRef} />
//         </div>
//         <div className={`input-section ${submitted ? 'input-bottom' : ''}`}>
//           {showLocation && (
//             <div className="input-box">
//               <textarea
//                 className="input-bar"
//                 placeholder={'Enter location (city or county)'}
//                 value={inputLocationText}
//                 onChange={handleInputChangeLocation}
//                 rows={1}
//               />
//             </div>
//           )}
//           <div className="input-box">
//             <textarea
//               className="input-bar"
//               ref={inputRef}
//               placeholder={
//                 submitted
//                   ? 'Write a follow-up to update...'
//                   : 'Describe the service user’s situation...'
//               }
//               value={inputText}
//               onChange={handleInputChange}
//               onKeyDown={handleKeyDown}
//               rows={1}
//               style={{ overflow: 'hidden', resize: 'none' }}
//             />
//             <button className="submit-button" onClick={handleSubmit}>
//               ➤
//             </button>
//           </div>
//           <div className="backend-selector-div">
//             <select
//               onChange={handleModelChange}
//               value={modelSelect}
//               name="model"
//               id="model"
//               className="backend-select"
//             >
//               <option value="copilot">Option A</option>
//               <option value="chatgpt">Option B</option>
//             </select>
//             <button
//               className="submit-button"
//               style={{ width: '100px', height: '100%', marginLeft: '20px' }}
//               onClick={handleNewSession}
//             >
//               Reset Session
//             </button>
//             <button
//               className="submit-button"
//               style={{ width: '150px', height: '100%', marginLeft: '20px' }}
//               onClick={exportChatToPDF}
//             >
//               Save Session History
//             </button>
//           </div>
//         </div>
//       </div>
//     </div>
//   );
// }

// export const ResourceRecommendation = () => (
//   <GenericChat
//     context={ResourceContext}
//     title="Resource Database"
//     baseUrl={`http://${window.location.hostname}:8000/resource_response/`}
//     showLocation={true}
//   />
// );

// export const WellnessGoals = () => (
//   <GenericChat
//     context={WellnessContext}
//     title="Wellness Goals"
//     baseUrl={`http://${window.location.hostname}:8000/wellness_response/`}
//     showLocation={false}
//   />
// );

// export const BenefitEligibility = () => (
//   <GenericChat
//     context={BenefitContext}
//     title="Benefit Eligibility"
//     baseUrl={`http://${window.location.hostname}:8000/benefit_response/`}
//     showLocation={false}
//   />
// );

// export default GenericChat;
import React, { useRef, useContext, useEffect, useState } from 'react';
import '../styles/feature.css';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import ReactMarkdown from 'react-markdown';
import { jsPDF } from 'jspdf';
import { BenefitContext, ResourceContext, WellnessContext } from './AppStateContextProvider.js';

function GenericChat({ context, title, baseUrl, showLocation }) {
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

  const inputRef = useRef(null); // For dynamic textarea height
  const conversationEndRef = useRef(null);

  // Refs to persist connection state between renders.
  const abortControllerRef = useRef(new AbortController());
  const isRequestInProgressRef = useRef(false);
  const pendingMessageRef = useRef(""); // Stores the message that started the fetch

  // NEW: Store the last event ID from the server.
  const lastEventIdRef = useRef(null);

  const [isResponseComplete, setIsResponseComplete] = useState(true);

  const handleInputChange = (e) => {
    setInputText(e.target.value);
    adjustTextareaHeight(e.target);
  };

  const handleModelChange = (e) => setModel(e.target.value);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // resumeFetch: Reconnects the SSE connection using the stored lastEventId.
  const resumeFetch = async () => {
    if (isResponseComplete || isRequestInProgressRef.current) return;

    // Reinitialize the abort controller.
    abortControllerRef.current = new AbortController();
    isRequestInProgressRef.current = true;

    // Clear leftover message content.
    setNewMessage('');
    // Use the saved pending message.
    const pendingMessage = pendingMessageRef.current;
    const botMessage = { sender: "bot", text: "Loading..." };
    setConversation((prev) => [...prev, botMessage]);

    try {
      await fetchEventSource(baseUrl, {
        method: "POST",
        headers: { 
          Accept: "text/event-stream", 
          "Content-Type": "application/json",
          // Send Last-Event-ID header if supported by your server.
          "Last-Event-ID": lastEventIdRef.current || ""
        },
        // Pass lastEventId as an option if your fetchEventSource library supports it.
        lastEventId: lastEventIdRef.current,
        signal: abortControllerRef.current.signal,
        body: JSON.stringify({
          text: pendingMessage,
          previous_text: chatConvo,
          model: modelSelect
        }),
        onmessage(event) {
          // If the event has an ID, store it.
          if (event.id) {
            lastEventIdRef.current = event.id;
          }
          setNewMessage((prev) => {
            const updatedMessage = prev + event.data.replaceAll("<br/>", "\n");
            const botMsg = { sender: "bot", text: updatedMessage };
            setConversation((convPrev) => {
              if (convPrev.length > 0) {
                return [...convPrev.slice(0, -1), botMsg];
              }
              return [botMsg];
            });
            return updatedMessage;
          });
        },
        onerror(err) {
          console.error("SSE onerror in resumeFetch:", err);
          isRequestInProgressRef.current = false;
          if (!isResponseComplete && document.visibilityState === 'visible') {
            setTimeout(() => {
              resumeFetch();
            }, 1000);
          }
        },
        onclose() {
          setIsResponseComplete(true);
          isRequestInProgressRef.current = false;
        },
      });
    } catch (err) {
      console.error("Fetch failed in resumeFetch:", err);
      isRequestInProgressRef.current = false;
    }
  };

  const handleInputChangeLocation = (e) => setInputLocationText(e.target.value);

  const handleNewSession = async () => {
    abortControllerRef.current.abort();
    abortControllerRef.current = new AbortController();
    resetContext();
  };

  const handleSubmit = async () => {
    if (inputText.trim() && !isRequestInProgressRef.current) {
      if (abortControllerRef.current.signal.aborted) {
        abortControllerRef.current = new AbortController();
      }

      // Build the message (including location) and store it.
      const newMessageText = inputText.trim() + "\n Location: " + (inputLocationText.trim() || "New Jersey");
      pendingMessageRef.current = newMessageText;
      // Reset lastEventId since this is a new request.
      lastEventIdRef.current = null;

      const userMessage = { sender: 'user', text: inputText.trim() };
      setConversation((prev) => [...prev, userMessage]);
      setInputText('');
      setChatConvo((prev) => [...prev, { role: 'user', content: inputText.trim() }]);
      setNewMessage("");
      setIsResponseComplete(false);

      const botMessage = { sender: "bot", text: "Loading..." };
      setConversation((prev) => [...prev, botMessage]);

      isRequestInProgressRef.current = true;

      try {
        await fetchEventSource(baseUrl, {
          method: "POST",
          headers: { 
            Accept: "text/event-stream", 
            'Content-Type': 'application/json',
            "Last-Event-ID": lastEventIdRef.current || ""
          },
          lastEventId: lastEventIdRef.current,
          signal: abortControllerRef.current.signal,
          body: JSON.stringify({ text: newMessageText, previous_text: chatConvo, model: modelSelect }),
          onmessage(event) {
            if (event.id) {
              lastEventIdRef.current = event.id;
            }
            setNewMessage((prev) => {
              const updatedMessage = prev + event.data.replaceAll("<br/>", "\n");
              const botMsg = { sender: "bot", text: updatedMessage };
              setConversation((convPrev) => {
                if (convPrev.length > 0) {
                  return [...convPrev.slice(0, -1), botMsg];
                }
                return [botMsg];
              });
              return updatedMessage;
            });
          },
          onerror(err) {
            console.error("SSE onerror in handleSubmit:", err);
            isRequestInProgressRef.current = false;
            if (!isResponseComplete && document.visibilityState === 'visible') {
              setTimeout(() => {
                resumeFetch();
              }, 1000);
            }
          },
          onclose() {
            setIsResponseComplete(true);
            isRequestInProgressRef.current = false;
          },
        });
      } catch (err) {
        console.error("Fetch failed in handleSubmit:", err);
      } finally {
        isRequestInProgressRef.current = false;
      }
    }
  };

  const adjustTextareaHeight = (textarea) => {
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${textarea.scrollHeight}px`;
    }
  };

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        if (!isResponseComplete && !isRequestInProgressRef.current) {
          abortControllerRef.current.abort();
          abortControllerRef.current = new AbortController();
          resumeFetch();
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [isResponseComplete, chatConvo, modelSelect]);

  useEffect(() => {
    if (inputRef.current) {
      adjustTextareaHeight(inputRef.current);
    }
  }, [inputText]);

  useEffect(() => {
    if (conversationEndRef.current) {
      setTimeout(() => {
        conversationEndRef.current.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    }
  }, [conversation]);

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

  return (
    <div className="resource-recommendation-container">
      <div className={`left-section ${submitted ? 'submitted' : ''}`}>
        <h1 className="page-title">{title}</h1>
        <h2 className="instruction">
          What is the service user’s needs and goals for today’s meeting?
        </h2>
        <div className={`conversation-thread ${submitted ? 'visible' : ''}`}>
          {conversation.map((msg, index) => (
            <div key={index} className={`message-blurb ${msg.sender === 'user' ? 'user' : 'bot'}`}>
              <ReactMarkdown
                children={msg.text}
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
        <div className={`input-section ${submitted ? 'input-bottom' : ''}`}>
          {showLocation && (
            <div className="input-box">
              <textarea
                className="input-bar"
                placeholder={'Enter location (city or county)'}
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
          <div className="backend-selector-div">
            <select
              onChange={handleModelChange}
              value={modelSelect}
              name="model"
              id="model"
              className="backend-select"
            >
              <option value="copilot">Option A</option>
              <option value="chatgpt">Option B</option>
            </select>
            <button
              className="submit-button"
              style={{ width: '100px', height: '100%', marginLeft: '20px' }}
              onClick={handleNewSession}
            >
              Reset Session
            </button>
            <button
              className="submit-button"
              style={{ width: '150px', height: '100%', marginLeft: '20px' }}
              onClick={exportChatToPDF}
            >
              Save Session History
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export const ResourceRecommendation = () => (
  <GenericChat
    context={ResourceContext}
    title="Resource Database"
    baseUrl={`http://${window.location.hostname}:8000/resource_response/`}
    showLocation={true}
  />
);

export const WellnessGoals = () => (
  <GenericChat
    context={WellnessContext}
    title="Wellness Goals"
    baseUrl={`http://${window.location.hostname}:8000/wellness_response/`}
    showLocation={false}
  />
);

export const BenefitEligibility = () => (
  <GenericChat
    context={BenefitContext}
    title="Benefit Eligibility"
    baseUrl={`http://${window.location.hostname}:8000/benefit_response/`}
    showLocation={false}
  />
);

export default GenericChat;
