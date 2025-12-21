// Kunwar - 29604570
// Main chat application component for AI-powered code generation

import React, { useState, useRef, useEffect, useCallback } from 'react';
import Editor from '@monaco-editor/react';
import { 
  Send, Code, CheckCircle, Loader2,
  FolderTree, FileCode, ChevronRight, ChevronDown,
  Sparkles, Bot, User, Rocket, ExternalLink,
  RefreshCw, Square, Globe, Terminal, Eye, MonitorPlay,
  Zap, AlertCircle, Maximize2, Activity
} from 'lucide-react';
import LLMUsageTracker from './components/LLMUsageTracker';

// Backend API URL - defaults to localhost for development
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  metadata?: any;
}

interface Feature {
  id: string;
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  category: string;
}

interface CodeFile {
  filename: string;
  filepath: string;
  content: string;
  language: string;
}

interface FileNode {
  name: string;
  type: 'file' | 'folder';
  path: string;
  children?: FileNode[];
}

// Tracks the state of the generated application's execution
interface AppExecutionState {
  status: 'idle' | 'starting' | 'running' | 'stopped' | 'error';
  url: string | null;
  port: number | null;
  logs: string[];
  error: string | null;
  projectPath: string | null;
}

type ActiveTab = 'editor' | 'preview' | 'console';

function ChatApp() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [proposedFeatures, setProposedFeatures] = useState<Feature[]>([]);
  const [codeFiles, setCodeFiles] = useState<CodeFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<CodeFile | null>(null);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['root']));
  const [isGenerationComplete, setIsGenerationComplete] = useState(false);
  
  const [appExecution, setAppExecution] = useState<AppExecutionState>({
    status: 'idle',
    url: null,
    port: null,
    logs: [],
    error: null,
    projectPath: null
  });
  
  const [activeTab, setActiveTab] = useState<ActiveTab>('editor');
  const [showExecuteButton, setShowExecuteButton] = useState(false);
  const [previewWindow, setPreviewWindow] = useState<Window | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);
  const [showLLMUsageTracker, setShowLLMUsageTracker] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const codeScrollRef = useRef<HTMLDivElement>(null);
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
  const chatInputRef = useRef<HTMLTextAreaElement>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [appExecution.logs]);

  useEffect(() => {
    return () => {
      if (readerRef.current) {
        readerRef.current.cancel().catch(console.error);
      }
    };
  }, []);

  useEffect(() => {
    if (isGenerationComplete && codeFiles.length > 0) {
      const timer = setTimeout(() => {
        setShowExecuteButton(true);
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [isGenerationComplete, codeFiles.length]);

  const openPreviewWindow = useCallback(() => {
    if (appExecution.url) {
      const newWindow = window.open(
        appExecution.url,
        'preview_window',
        'width=1200,height=800,menubar=no,toolbar=no,location=yes,status=yes,scrollbars=yes,resizable=yes'
      );
      setPreviewWindow(newWindow);
    }
  }, [appExecution.url]);

  const executeApplication = useCallback(async () => {
    if (codeFiles.length === 0) return;

    setAppExecution(prev => ({
      ...prev,
      status: 'starting',
      logs: ['🚀 Starting application...'],
      error: null
    }));
    
    setActiveTab('console');

    try {
      const response = await fetch(`${API_URL}/api/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          files: codeFiles,
          conversation_id: conversationId
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to execute application');
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No reader available');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.trim() || !line.startsWith('data: ')) continue;

          try {
            const data = JSON.parse(line.slice(6));
            
            switch (data.type) {
              case 'log':
                setAppExecution(prev => ({
                  ...prev,
                  logs: [...prev.logs, data.message]
                }));
                break;
                
              case 'started':
                setAppExecution(prev => ({
                  ...prev,
                  status: 'running',
                  url: data.url,
                  port: data.port,
                  projectPath: data.project_path,
                  logs: [...prev.logs, `✅ Application running at ${data.url}`]
                }));
                setActiveTab('preview');
                break;
                
              case 'error':
                setAppExecution(prev => ({
                  ...prev,
                  status: 'error',
                  error: data.message,
                  logs: [...prev.logs, `❌ Error: ${data.message}`]
                }));
                break;
            }
          } catch (e) {
            console.error('Parse error:', e);
          }
        }
      }
    } catch (error: any) {
      setAppExecution(prev => ({
        ...prev,
        status: 'error',
        error: error.message,
        logs: [...prev.logs, `❌ Error: ${error.message}`]
      }));
    }
  }, [codeFiles, conversationId]);

  const stopApplication = useCallback(async () => {
    if (!appExecution.projectPath) return;

    try {
      await fetch(`${API_URL}/api/execute/stop`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: appExecution.projectPath
        })
      });

      setAppExecution(prev => ({
        ...prev,
        status: 'stopped',
        logs: [...prev.logs, '🛑 Application stopped']
      }));
      
      if (previewWindow && !previewWindow.closed) {
        previewWindow.close();
      }
    } catch (error: any) {
      console.error('Failed to stop application:', error);
    }
  }, [appExecution.projectPath, previewWindow]);

  const sendMessage = async () => {
    if (!inputMessage.trim() || isProcessing) return;

    setIsGenerationComplete(false);
    setShowExecuteButton(false);

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsProcessing(true);

    try {
      const response = await fetch(`${API_URL}/api/chat/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: conversationId,
          message: inputMessage
        })
      });

      if (!response.ok) throw new Error('Failed to send message');

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No reader available');

      readerRef.current = reader;
      const decoder = new TextDecoder();
      let buffer = '';
      let assistantMessage = '';

      const streamingMessageId = Date.now().toString();
      setMessages(prev => [...prev, {
        id: streamingMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString()
      }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.trim() || !line.startsWith('data: ')) continue;

          try {
            const data = JSON.parse(line.slice(6));
            
            switch (data.type) {
              case 'started':
                if (!conversationId && data.conversation_id !== 'new') {
                  setConversationId(data.conversation_id);
                }
                break;

              case 'phase_change':
                const phaseMsg = `\n🔄 ${data.data.message}\n\n`;
                assistantMessage += phaseMsg;
                setMessages(prev => prev.map(msg => 
                  msg.id === streamingMessageId 
                    ? { ...msg, content: assistantMessage }
                    : msg
                ));
                break;

              case 'features_proposed':
                if (!conversationId && data.data.conversation_id) {
                  setConversationId(data.data.conversation_id);
                }
                const features = data.data.features || [];
                setProposedFeatures(features);
                break;

              case 'file_generated':
                const file = data.data;
                setCodeFiles(prev => {
                  const existingIndex = prev.findIndex(f => f.filepath === file.filepath);
                  if (existingIndex >= 0) {
                    const updated = [...prev];
                    updated[existingIndex] = file;
                    return updated;
                  }
                  return [...prev, file];
                });
                if (!selectedFile) {
                  setSelectedFile(file);
                }
                const fileMsg = `\n✅ Generated: \`${file.filename}\`\n`;
                assistantMessage += fileMsg;
                setMessages(prev => prev.map(msg => 
                  msg.id === streamingMessageId 
                    ? { ...msg, content: assistantMessage }
                    : msg
                ));
                if (codeScrollRef.current) {
                  codeScrollRef.current.scrollTop = codeScrollRef.current.scrollHeight;
                }
                break;

              case 'code_generated':
                assistantMessage += `\n${data.data.message}\n`;
                const files = data.data.files || [];
                if (files.length > 0) {
                  setCodeFiles(files);
                  if (!selectedFile) {
                    setSelectedFile(files[0]);
                  }
                }
                setMessages(prev => prev.map(msg => 
                  msg.id === streamingMessageId 
                    ? { ...msg, content: assistantMessage }
                    : msg
                ));
                setIsGenerationComplete(true);
                break;

              case 'message_end':
                if (!conversationId && data.data.conversation_id) {
                  setConversationId(data.data.conversation_id);
                }
                assistantMessage += data.data.message || '';
                setMessages(prev => prev.map(msg => 
                  msg.id === streamingMessageId 
                    ? { ...msg, content: assistantMessage }
                    : msg
                ));
                break;

              case 'implementation_started':
                const implMsg = `\n🚀 ${data.data.message}\n`;
                assistantMessage += implMsg;
                setMessages(prev => prev.map(msg => 
                  msg.id === streamingMessageId 
                    ? { ...msg, content: assistantMessage }
                    : msg
                ));
                break;

              case 'error':
                assistantMessage += `\n❌ ERROR: ${data.data.error}\n`;
                setMessages(prev => prev.map(msg => 
                  msg.id === streamingMessageId 
                    ? { ...msg, content: assistantMessage }
                    : msg
                ));
                break;
            }
          } catch (e) {
            console.error('Parse error:', e);
          }
        }
      }

      if (assistantMessage.trim()) {
        setMessages(prev => prev.map(msg => 
          msg.id === streamingMessageId 
            ? { ...msg, content: assistantMessage.trim() }
            : msg
        ));
      } else {
        setMessages(prev => prev.filter(msg => msg.id !== streamingMessageId));
      }

      readerRef.current = null;
    } catch (error) {
      console.error('Error:', error);
      const errorMessage: Message = {
        id: Date.now().toString(),
        role: 'system',
        content: '[ERROR] Failed to process message. Please try again.',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsProcessing(false);
    }
  };

  const buildTree = (files: CodeFile[]): FileNode => {
    const root: FileNode = { name: 'root', type: 'folder', path: 'root', children: [] };
    
    files.forEach(file => {
      const parts = file.filepath.split('/').filter(p => p.trim());
      let currentNode = root;
      
      parts.forEach((part, index) => {
        if (!currentNode.children) currentNode.children = [];
        
        let childNode = currentNode.children.find(c => c.name === part);
        
        if (!childNode) {
          childNode = {
            name: part,
            type: index === parts.length - 1 ? 'file' : 'folder',
            path: parts.slice(0, index + 1).join('/'),
            children: index === parts.length - 1 ? undefined : []
          };
          currentNode.children.push(childNode);
        }
        
        currentNode = childNode;
      });
    });
    
    return root;
  };

  const toggleFolder = (path: string) => {
    setExpandedFolders(prev => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  };

  const renderTreeNode = (node: FileNode, depth: number = 0): React.ReactNode => {
    const isExpanded = expandedFolders.has(node.path);
    const isSelected = selectedFile?.filepath === node.path;

    if (node.type === 'folder') {
      return (
        <div key={node.path}>
          <div
            className={`flex items-center gap-2 px-2 py-1.5 cursor-pointer transition-colors ${
              isSelected ? 'bg-gray-700/50' : 'hover:bg-gray-700/30'
            }`}
            style={{ paddingLeft: `${depth * 12 + 8}px` }}
            onClick={() => toggleFolder(node.path)}
          >
            {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            <FolderTree size={14} className="text-blue-400" />
            <span className="text-xs text-gray-200 truncate">{node.name}</span>
          </div>
          {isExpanded && node.children && (
            <div>
              {node.children.map(child => renderTreeNode(child, depth + 1))}
            </div>
          )}
        </div>
      );
    }

    const file = codeFiles.find(f => f.filepath === node.path);
    return (
      <div
        key={node.path}
        className={`flex items-center gap-2 px-2 py-1.5 cursor-pointer transition-all ${
          isSelected ? 'bg-violet-600/30 border-l-2 border-violet-500' : 'hover:bg-gray-700/30'
        }`}
        style={{ paddingLeft: `${depth * 12 + 24}px` }}
        onClick={() => file && setSelectedFile(file)}
      >
        <FileCode size={14} className="text-gray-400" />
        <span className="text-xs text-gray-300 truncate">{node.name}</span>
      </div>
    );
  };

  const tree = codeFiles.length > 0 ? buildTree(codeFiles) : null;

  const downloadSourceCode = useCallback(async () => {
    if (codeFiles.length === 0) return;
    
    setIsDownloading(true);
    try {
      const response = await fetch(`${API_URL}/api/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          files: codeFiles
        })
      });
      
      if (!response.ok) throw new Error('Download failed');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = 'source-code.zip';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch) filename = filenameMatch[1];
      }
      
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download error:', error);
    } finally {
      setIsDownloading(false);
    }
  }, [codeFiles]);

  const renderExecuteButton = () => {
    if (!showExecuteButton) return null;

    return (
      <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2 z-50 animate-bounce-in flex gap-4">
        <button
          onClick={executeApplication}
          disabled={appExecution.status === 'starting'}
          className="btn-execute pulse-green flex items-center gap-3 shadow-lg shadow-emerald-500/20"
        >
          {appExecution.status === 'starting' ? (
            <>
              <Loader2 className="animate-spin" size={20} />
              <span>Starting Application...</span>
            </>
          ) : (
            <>
              <Rocket size={20} />
              <span>Execute Application</span>
              <Zap size={16} className="text-yellow-300" />
            </>
          )}
        </button>
        
        <button
          onClick={downloadSourceCode}
          disabled={isDownloading}
          className="px-6 py-3 bg-violet-600 hover:bg-violet-500 text-white rounded-full font-semibold transition-all transform hover:scale-105 active:scale-95 flex items-center gap-3 shadow-lg shadow-violet-500/20"
        >
          {isDownloading ? (
            <Loader2 className="animate-spin" size={20} />
          ) : (
            <div className="flex items-center gap-2">
              <span className="border-b-2 border-white pb-0.5">Download Source</span>
            </div>
          )}
        </button>
      </div>
    );
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'preview':
        return (
          <div className="flex-1 flex flex-col bg-gray-900">
            {appExecution.status === 'running' && appExecution.url ? (
              <>
                <div className="bg-gray-800 border-b border-gray-700 px-4 py-3 flex items-center justify-between shrink-0">
                  <div className="flex items-center gap-3">
                    <div className="flex gap-1.5">
                      <div className="w-3 h-3 rounded-full bg-red-500" />
                      <div className="w-3 h-3 rounded-full bg-yellow-500" />
                      <div className="w-3 h-3 rounded-full bg-green-500" />
                    </div>
                    <div className="flex items-center gap-2 bg-gray-700 rounded-lg px-3 py-1.5">
                      <Globe size={14} className="text-green-400" />
                      <span className="text-sm text-gray-300 font-mono">{appExecution.url}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        const iframe = document.querySelector('iframe[title="Application Preview"]') as HTMLIFrameElement;
                        if (iframe && appExecution.url) {
                          iframe.src = appExecution.url;
                        }
                      }}
                      className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
                      title="Refresh preview"
                    >
                      <RefreshCw size={18} className="text-gray-400 hover:text-white" />
                    </button>
                    <button
                      onClick={openPreviewWindow}
                      className="btn-primary flex items-center gap-2 text-sm"
                      title="Open in new window"
                    >
                      <Maximize2 size={16} />
                      Open App
                    </button>
                    <a
                      href={appExecution.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
                      title="Open in browser tab"
                    >
                      <ExternalLink size={18} className="text-gray-400 hover:text-white" />
                    </a>
                    <button
                      onClick={stopApplication}
                      className="p-2 hover:bg-red-600/20 rounded-lg transition-colors"
                      title="Stop application"
                    >
                      <Square size={18} className="text-red-400 hover:text-red-300" />
                    </button>
                  </div>
                </div>
                
                {/* Embedded iframe preview */}
                <div className="flex-1 relative bg-white overflow-hidden">
                  <iframe
                    src={appExecution.url}
                    className="absolute inset-0 w-full h-full border-0"
                    title="Application Preview"
                    sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-modals allow-downloads"
                    allow="accelerometer; camera; encrypted-media; geolocation; gyroscope; microphone; midi; payment; usb"
                  />
                  {/* Loading overlay */}
                  <div className="absolute top-4 right-4 bg-black/70 backdrop-blur-sm rounded-lg px-3 py-1.5 flex items-center gap-2 pointer-events-none">
                    <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="text-xs text-white font-medium">Live Preview</span>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center p-8">
                  {appExecution.status === 'starting' ? (
                    <>
                      <Loader2 size={48} className="mx-auto mb-4 text-emerald-400 animate-spin" />
                      <h3 className="text-lg font-semibold text-white mb-2">Starting Application...</h3>
                      <p className="text-sm text-gray-400">Installing dependencies and starting the server</p>
                    </>
                  ) : appExecution.status === 'error' ? (
                    <>
                      <AlertCircle size={48} className="mx-auto mb-4 text-red-400" />
                      <h3 className="text-lg font-semibold text-white mb-2">Failed to Start</h3>
                      <p className="text-sm text-red-400 max-w-md">{appExecution.error}</p>
                      <button
                        onClick={executeApplication}
                        className="mt-4 btn-primary flex items-center gap-2 mx-auto"
                      >
                        <RefreshCw size={16} />
                        Retry
                      </button>
                    </>
                  ) : (
                    <>
                      <MonitorPlay size={48} className="mx-auto mb-4 text-gray-500" />
                      <h3 className="text-lg font-semibold text-gray-400 mb-2">No Application Running</h3>
                      <p className="text-sm text-gray-500">Click "Execute Application" to run your generated code</p>
                    </>
                  )}
                </div>
              </div>
            )}
          </div>
        );

      case 'console':
        return (
          <div className="flex-1 flex flex-col bg-gray-950">
            <div className="bg-gray-800 border-b border-gray-700 px-4 py-2 flex items-center gap-3 shrink-0">
              <Terminal size={16} className="text-emerald-400" />
              <span className="text-sm font-medium text-gray-200">Console Output</span>
              {appExecution.status === 'running' && (
                <span className="badge-green text-xs ml-auto">Running</span>
              )}
            </div>
            <div className="flex-1 overflow-y-auto p-4 font-mono text-sm scrollbar scrollbar-w-3 scrollbar-thumb-amber-500 scrollbar-track-gray-900 hover:scrollbar-thumb-amber-400">
              {appExecution.logs.length === 0 ? (
                <div className="text-gray-500 italic">No logs yet...</div>
              ) : (
                appExecution.logs.map((log, i) => (
                  <div key={i} className={`py-0.5 ${
                    log.includes('❌') ? 'text-red-400' :
                    log.includes('✅') ? 'text-emerald-400' :
                    log.includes('🚀') ? 'text-blue-400' :
                    log.includes('📦') ? 'text-yellow-400' :
                    log.includes('📁') ? 'text-cyan-400' :
                    log.includes('💾') ? 'text-purple-400' :
                    log.includes('⚠️') ? 'text-orange-400' :
                    'text-gray-300'
                  }`}>
                    {log}
                  </div>
                ))
              )}
              <div ref={logsEndRef} />
            </div>
          </div>
        );

      default:
        return (
          <>
            {selectedFile ? (
              <>
                <div className="bg-gray-800 border-b border-gray-700 px-4 py-2 flex items-center justify-between shrink-0">
                  <div className="flex items-center gap-2">
                    <Code size={16} className="text-violet-400" />
                    <span className="text-sm text-white font-medium">{selectedFile.filename}</span>
                  </div>
                  <span className="text-xs text-gray-400 badge-purple">{selectedFile.language.toUpperCase()}</span>
                </div>
                
                <div className="flex-1 min-h-0">
                  <Editor
                    height="100%"
                    language={selectedFile.language}
                    value={selectedFile.content}
                    theme="vs-dark"
                    options={{
                      readOnly: true,
                      minimap: { enabled: window.innerWidth > 1024 },
                      fontSize: 13,
                      lineNumbers: 'on',
                      scrollBeyondLastLine: false,
                      automaticLayout: true,
                      tabSize: 2,
                      wordWrap: 'on',
                      fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                      fontLigatures: true,
                      scrollbar: {
                        vertical: 'visible',
                        horizontal: 'visible',
                        useShadows: true,
                        verticalHasArrows: false,
                        horizontalHasArrows: false,
                        verticalScrollbarSize: 14,
                        horizontalScrollbarSize: 14,
                        arrowSize: 0,
                      },
                      overviewRulerBorder: false,
                      hideCursorInOverviewRuler: true,
                    }}
                  />
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center text-gray-500">
                <div className="text-center">
                  <FileCode size={48} className="mx-auto mb-4 opacity-20" />
                  <p className="text-sm">Select a file to view</p>
                </div>
              </div>
            )}
          </>
        );
    }
  };

  return (
    <div className="h-screen max-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex flex-col overflow-hidden">
      <header className="glass border-b border-gray-700/50 shadow-xl shrink-0">
        <div className="px-4 md:px-6 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Sparkles className="text-cyan-400" size={26} />
              <div>
                <h1 className="text-lg font-bold text-white">
                  AgentOverflow
                </h1>
                <p className="text-xs text-gray-400">
                  Enterprise Multi-Agent Platform
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowLLMUsageTracker(!showLLMUsageTracker)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all ${
                  showLLMUsageTracker
                    ? 'bg-violet-600 text-white'
                    : 'bg-gray-700/50 text-gray-300 hover:bg-gray-700'
                }`}
                title="Toggle LLM Usage Tracking"
              >
                <Activity size={16} />
                <span className="text-xs font-medium">Usage</span>
              </button>
              {appExecution.status === 'running' && (
                <span className="badge-green flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  App Running
                </span>
              )}
              {conversationId && (
                <span className="badge-cyan text-xs">
                  Session Active
                </span>
              )}
            </div>
          </div>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden relative min-h-0">
        {/* Chat Panel - Cyan Scrollbar */}
        <div className="w-full md:w-[35%] lg:w-[30%] glass-dark border-r border-gray-700/50 flex flex-col min-h-0">
          <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0 scrollbar scrollbar-w-3 scrollbar-thumb-cyan-500 scrollbar-track-gray-800/50 hover:scrollbar-thumb-cyan-400">
            {messages.length === 0 && (
              <div className="text-center py-8">
                <Bot size={40} className="mx-auto mb-3 text-cyan-400 opacity-50" />
                <h3 className="text-base font-semibold text-white mb-2">
                  Let's Build Something Amazing!
                </h3>
                <p className="text-sm text-gray-400 px-4">
                  Describe your application idea, and I'll help you build it.
                </p>
              </div>
            )}
            
            {messages.map(msg => (
              <div
                key={msg.id}
                className={`flex gap-3 ${
                  msg.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {msg.role === 'assistant' && (
                  <div className="flex-shrink-0">
                    <Bot size={22} className="text-cyan-400" />
                  </div>
                )}
                
                <div
                  className={`max-w-[85%] rounded-lg p-3 ${
                    msg.role === 'user'
                      ? 'bg-cyan-600 text-white'
                      : msg.role === 'system'
                      ? 'bg-red-500/20 text-red-200 border border-red-500/30'
                      : 'bg-gray-700/50 text-gray-200'
                  }`}
                >
                  <div className="text-sm whitespace-pre-wrap break-words">
                    {msg.content}
                  </div>
                  <div className="text-xs opacity-60 mt-1">
                    {new Date(msg.timestamp).toLocaleTimeString()}
                  </div>
                </div>
                
                {msg.role === 'user' && (
                  <div className="flex-shrink-0">
                    <User size={22} className="text-gray-400" />
                  </div>
                )}
              </div>
            ))}
            
            {isProcessing && (
              <div className="flex gap-3">
                <Bot size={22} className="text-cyan-400 animate-pulse" />
                <div className="bg-gray-700/50 rounded-lg p-3">
                  <Loader2 className="animate-spin text-cyan-400" size={18} />
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {proposedFeatures.length > 0 && (
            <div className="border-t border-gray-700/50 p-3 max-h-36 overflow-y-auto shrink-0 scrollbar scrollbar-w-2 scrollbar-thumb-cyan-500/50 scrollbar-track-transparent">
              <h4 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
                <CheckCircle size={14} className="text-emerald-400" />
                Features ({proposedFeatures.length})
              </h4>
              <div className="space-y-1.5">
                {proposedFeatures.map(feat => {
                  // Check if any generated files relate to this feature (simple heuristic)
                  const isImplemented = codeFiles.some(file =>
                    file.filepath.toLowerCase().includes(feat.title.toLowerCase().split(' ')[0]) ||
                    file.content.toLowerCase().includes(feat.title.toLowerCase())
                  );

                  return (
                    <div key={feat.id} className="text-xs p-2 bg-gray-700/30 rounded">
                      <div className="flex items-start gap-2">
                        <span className={`mt-0.5 transition-colors ${
                          isImplemented ? 'text-emerald-400' : 'text-red-400'
                        }`}>•</span>
                        <div className="flex-1">
                          <div className="font-medium text-gray-200">{feat.title}</div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div className="border-t border-gray-700/50 p-3 shrink-0">
            <div className="flex gap-2">
              <textarea
                ref={chatInputRef}
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
                placeholder="Describe your app..."
                className="input flex-1 text-sm resize-none h-16 scrollbar scrollbar-w-2 scrollbar-thumb-cyan-500/50 scrollbar-track-transparent"
                disabled={isProcessing}
              />
              <button
                onClick={sendMessage}
                disabled={!inputMessage.trim() || isProcessing}
                className="btn-primary px-3 py-2 flex items-center justify-center"
              >
                {isProcessing ? (
                  <Loader2 className="animate-spin" size={18} />
                ) : (
                  <Send size={18} />
                )}
              </button>
            </div>
            <p className="text-[10px] text-gray-500 mt-1">
              Enter to send, Shift+Enter for new line
            </p>
          </div>
        </div>

        {/* Code Panel */}
        <div className="flex-1 flex flex-col bg-gray-900 min-h-0">
          {codeFiles.length > 0 ? (
            <>
              <div className="bg-gray-800 border-b border-gray-700 px-4 flex items-center gap-1 shrink-0">
                <button
                  onClick={() => setActiveTab('editor')}
                  className={activeTab === 'editor' ? 'tab-active' : 'tab-inactive'}
                >
                  <div className="flex items-center gap-2">
                    <Code size={14} />
                    <span>Editor</span>
                  </div>
                </button>
                <button
                  onClick={() => setActiveTab('preview')}
                  className={activeTab === 'preview' ? 'tab-active' : 'tab-inactive'}
                >
                  <div className="flex items-center gap-2">
                    <Eye size={14} />
                    <span>Live Preview</span>
                    {appExecution.status === 'running' && (
                      <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    )}
                  </div>
                </button>
                <button
                  onClick={() => setActiveTab('console')}
                  className={activeTab === 'console' ? 'tab-active' : 'tab-inactive'}
                >
                  <div className="flex items-center gap-2">
                    <Terminal size={14} />
                    <span>Console</span>
                    {appExecution.logs.length > 0 && (
                      <span className="text-[10px] badge bg-gray-700 text-gray-300">
                        {appExecution.logs.length}
                      </span>
                    )}
                  </div>
                </button>
              </div>

              <div className="flex flex-1 min-h-0">
                {activeTab === 'editor' && (
                  <div className="w-56 glass-dark border-r border-gray-700/50 flex flex-col min-h-0">
                    <div className="px-3 py-2 border-b border-gray-700/50 shrink-0">
                      <div className="flex items-center gap-2 text-gray-400 text-xs font-semibold">
                        <FolderTree size={14} className="text-violet-400" />
                        <span>EXPLORER</span>
                        <span className="ml-auto badge-purple text-[10px]">{codeFiles.length}</span>
                      </div>
                    </div>
                    {/* File Tree - Gray Scrollbar */}
                    <div ref={codeScrollRef} className="flex-1 overflow-y-auto min-h-0 scrollbar scrollbar-w-2 scrollbar-thumb-gray-600 scrollbar-track-transparent hover:scrollbar-thumb-gray-500">
                      {tree && tree.children && tree.children.map(child => renderTreeNode(child, 0))}
                    </div>
                  </div>
                )}

                <div className="flex-1 flex flex-col min-h-0">
                  {renderTabContent()}
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-500">
              <div className="text-center p-8">
                <Code size={56} className="mx-auto mb-4 opacity-20" />
                <h3 className="text-lg font-semibold text-gray-400 mb-2">
                  No Code Yet
                </h3>
                <p className="text-sm text-gray-500 max-w-md">
                  Start chatting to generate your application!
                </p>
              </div>
            </div>
          )}
        </div>

        {renderExecuteButton()}
      </div>

      {/* LLM Usage Tracker */}
      {showLLMUsageTracker && (
        <LLMUsageTracker
          onClose={() => setShowLLMUsageTracker(false)}
          autoRefresh={true}
          refreshInterval={3000}
        />
      )}
    </div>
  );
}

export default ChatApp;
