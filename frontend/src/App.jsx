import React, { useEffect, useState } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import {
  checkHealth,
  clearConversation,
  deleteDocument,
  fetchDocuments,
  fetchSessionMemory,
  sendChatMessage,
  uploadDocument,
} from './api/client';

export default function App() {
  const [sessions, setSessions] = useState([
    { session_id: 'default', title: 'Main Session' },
  ]);
  const [currentSessionId, setCurrentSessionId] = useState('default');
  const [messages, setMessages] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [health, setHealth] = useState({ ollama: false, models: [] });
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  // Poll health and load documents on mount
  useEffect(() => {
    const loadInitData = async () => {
      const h = await checkHealth();
      setHealth(h);

      try {
        const docs = await fetchDocuments();
        setDocuments(docs || []);
      } catch (err) {
        console.warn('Could not load documents initially:', err);
      }
    };

    loadInitData();
    const interval = setInterval(async () => {
      const h = await checkHealth();
      setHealth(h);
    }, 15000);

    return () => clearInterval(interval);
  }, []);

  // When switching session, load history from DB if available
  useEffect(() => {
    const loadSessionMessages = async () => {
      if (!currentSessionId) return;
      try {
        const memoryData = await fetchSessionMemory(currentSessionId);
        if (memoryData?.messages && memoryData.messages.length > 0) {
          const formatted = memoryData.messages.map((m) => ({
            role: m.role || 'user',
            content: m.content || '',
            timestamp: m.created_at
              ? new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              : undefined,
          }));
          setMessages(formatted);
        } else {
          setMessages([]);
        }
      } catch (err) {
        console.info('Session memory empty or new session:', err);
        setMessages([]);
      }
    };

    loadSessionMessages();
  }, [currentSessionId]);

  // Handle sending a message
  const handleSendMessage = async (text) => {
    const userMsg = {
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const result = await sendChatMessage(text, currentSessionId);
      const assistantMsg = {
        role: 'assistant',
        content: result.answer || 'No answer generated.',
        debug: result.debug,
        plan: result.plan,
        critic: result.critic,
        sources: result.sources,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, assistantMsg]);

      // Update session title if first turn
      setSessions((prev) =>
        prev.map((s) =>
          s.session_id === currentSessionId && s.title === 'Main Session'
            ? { ...s, title: text.slice(0, 30) + '...' }
            : s
        )
      );
    } catch (err) {
      const errorMsg = {
        role: 'assistant',
        content: `Error: ${err.message || 'Failed to process request.'}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle uploading a document
  const handleUploadDocument = async (file) => {
    setIsUploading(true);
    try {
      const result = await uploadDocument(file);
      alert(`Successfully indexed "${result.filename}" (${result.chunks_indexed || 0} chunks).`);
      const updatedDocs = await fetchDocuments();
      setDocuments(updatedDocs || []);
    } catch (err) {
      alert(`Upload error: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  // Handle deleting a document
  const handleDeleteDocument = async (docId) => {
    if (!window.confirm('Are you sure you want to delete this document from the knowledge catalog?')) {
      return;
    }
    try {
      await deleteDocument(docId);
      setDocuments((prev) => prev.filter((d) => d.document_id !== docId));
    } catch (err) {
      alert(`Delete error: ${err.message}`);
    }
  };

  // Handle New Chat
  const handleNewChat = () => {
    const newId = `session-${Date.now()}`;
    const newSession = { session_id: newId, title: `Chat ${sessions.length + 1}` };
    setSessions((prev) => [newSession, ...prev]);
    setCurrentSessionId(newId);
    setMessages([]);
  };

  // Handle Clear Chat
  const handleClearChat = async () => {
    if (!window.confirm('Clear all conversation messages in the current session?')) return;
    try {
      await clearConversation();
      setMessages([]);
    } catch (err) {
      console.warn('Failed to clear conversation:', err);
      setMessages([]);
    }
  };

  return (
    <div className="app-container">
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={setCurrentSessionId}
        onNewChat={handleNewChat}
        documents={documents}
        onUploadDocument={handleUploadDocument}
        onDeleteDocument={handleDeleteDocument}
        isUploading={isUploading}
        health={health}
      />

      <main className="main-content">
        <Header
          health={health}
          onClearChat={handleClearChat}
          criticEnabled={true}
          documentCount={documents.length}
        />

        <ChatWindow
          messages={messages}
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
        />
      </main>
    </div>
  );
}
