import React, { useState, useRef, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import { 
  Send, Code, MessageSquare, CheckCircle, Loader2,
  FolderTree, FileCode, ChevronRight, ChevronDown, X,
  Sparkles, Play, Bot, User
} from 'lucide-react';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8500';

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

function ChatApp() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [phase, setPhase] = useState('initial');
  const [proposedFeatures, setProposedFeatures] = useState<Feature[]>([]);
  const [codeFiles, setCodeFiles] = useState<CodeFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<CodeFile | null>(null);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['root']));
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
  const chatInputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    return () => {
      if (readerRef.current) {
        readerRef.current.cancel().catch(console.error);
      }
    };
  }, []);

  const sendMessage = async () => {
    if (!inputMessage.trim() || isProcessing) return;

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
                setPhase(data.data.phase);
                assistantMessage += `\n[${data.data.message}]\n\n`;
                break;

              case 'features_proposed':
                const features = data.data.features || [];
                setProposedFeatures(features);
                break;

              case 'file_generated':
                const file = data.data;
                setCodeFiles(prev => [...prev, file]);
                if (!selectedFile) {
                  setSelectedFile(file);
                }
                break;

              case 'code_generated':
                assistantMessage += data.data.message;
                const files = data.data.files || [];
                setCodeFiles(files);
                if (files.length > 0 && !selectedFile) {
                  setSelectedFile(files[0]);
                }
                break;

              case 'message_end':
                assistantMessage += data.data.message || '';
                break;

              case 'error':
                assistantMessage += `\n[ERROR] ${data.data.error}\n`;
                break;
            }
          } catch (e) {
            console.error('Parse error:', e);
          }
        }
      }

      if (assistantMessage.trim()) {
        const aiMessage: Message = {
          id: Date.now().toString(),
          role: 'assistant',
          content: assistantMessage.trim(),
          timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, aiMessage]);
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
        <div key={node.path} className="animate-in">
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
            <div className="animate-in">
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
          isSelected ? 'bg-blue-600/30 border-l-2 border-blue-500' : 'hover:bg-gray-700/30'
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex flex-col">
      {/* Header */}
      <header className="glass border-b border-gray-700/50 shadow-xl sticky top-0 z-50">
        <div className="px-4 md:px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Sparkles className="text-blue-400" size={28} />
              <div>
                <h1 className="text-lg md:text-xl font-bold text-white">
                  AI Code Assistant
                </h1>
                <p className="text-xs text-gray-400">
                  Chat to build your Next.js application
                </p>
              </div>
            </div>
            {conversationId && (
              <span className="badge-blue text-xs">
                Session Active
              </span>
            )}
          </div>
        </div>
      </header>

      {/* Main Content - Split Screen */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Chat Interface (30%) */}
        <div className="w-full md:w-[35%] lg:w-[30%] glass-dark border-r border-gray-700/50 flex flex-col">
          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
            {messages.length === 0 && (
              <div className="text-center py-12 animate-in">
                <Bot size={48} className="mx-auto mb-4 text-blue-400 opacity-50" />
                <h3 className="text-lg font-semibold text-white mb-2">
                  Let's Build Something Amazing!
                </h3>
                <p className="text-sm text-gray-400 px-4">
                  Describe your application idea, and I'll help you plan and build it.
                </p>
              </div>
            )}
            
            {messages.map(msg => (
              <div
                key={msg.id}
                className={`flex gap-3 animate-in ${
                  msg.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {msg.role === 'assistant' && (
                  <div className="flex-shrink-0">
                    <Bot size={24} className="text-blue-400" />
                  </div>
                )}
                
                <div
                  className={`max-w-[85%] rounded-lg p-3 ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white'
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
                    <User size={24} className="text-gray-400" />
                  </div>
                )}
              </div>
            ))}
            
            {isProcessing && (
              <div className="flex gap-3 animate-in">
                <Bot size={24} className="text-blue-400 animate-pulse" />
                <div className="bg-gray-700/50 rounded-lg p-3">
                  <Loader2 className="animate-spin text-blue-400" size={20} />
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* Features Display */}
          {proposedFeatures.length > 0 && (
            <div className="border-t border-gray-700/50 p-4 max-h-48 overflow-y-auto">
              <h4 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
                <CheckCircle size={16} className="text-green-400" />
                Proposed Features ({proposedFeatures.length})
              </h4>
              <div className="space-y-2">
                {proposedFeatures.map(feat => (
                  <div key={feat.id} className="text-xs p-2 bg-gray-700/30 rounded">
                    <div className="flex items-start gap-2">
                      <span className={`mt-0.5 ${
                        feat.priority === 'high' ? 'text-red-400' :
                        feat.priority === 'medium' ? 'text-yellow-400' :
                        'text-gray-400'
                      }`}>•</span>
                      <div className="flex-1">
                        <div className="font-medium text-gray-200">{feat.title}</div>
                        <div className="text-gray-400 text-[10px] mt-0.5">{feat.description}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Chat Input */}
          <div className="border-t border-gray-700/50 p-4">
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
                placeholder="Describe your app or request changes..."
                className="input flex-1 text-sm resize-none h-20"
                disabled={isProcessing}
              />
              <button
                onClick={sendMessage}
                disabled={!inputMessage.trim() || isProcessing}
                className="btn-primary px-4 py-2 flex items-center justify-center"
              >
                {isProcessing ? (
                  <Loader2 className="animate-spin" size={20} />
                ) : (
                  <Send size={20} />
                )}
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Press Enter to send, Shift+Enter for new line
            </p>
          </div>
        </div>

        {/* Right: Code Display (70%) */}
        <div className="flex-1 flex flex-col bg-editor-bg overflow-hidden">
          {codeFiles.length > 0 ? (
            <>
              {/* File Explorer & Editor Split */}
              <div className="flex flex-1 overflow-hidden">
                {/* File Tree */}
                <div className="w-64 glass-dark border-r border-gray-700/50 flex flex-col">
                  <div className="px-3 py-3 border-b border-gray-700/50">
                    <div className="flex items-center gap-2 text-gray-400 text-xs font-semibold">
                      <FolderTree size={16} className="text-blue-400" />
                      <span>EXPLORER</span>
                      <span className="ml-auto badge-blue text-xs">{codeFiles.length}</span>
                    </div>
                  </div>
                  <div className="flex-1 overflow-y-auto scrollbar-thin">
                    {tree && tree.children && tree.children.map(child => renderTreeNode(child, 0))}
                  </div>
                </div>

                {/* Code Editor */}
                <div className="flex-1 flex flex-col">
                  {selectedFile ? (
                    <>
                      <div className="bg-editor-sidebar border-b border-editor-border px-4 py-2 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Code size={16} className="text-blue-400" />
                          <span className="text-sm text-white font-medium">{selectedFile.filename}</span>
                        </div>
                        <span className="text-xs text-gray-400">{selectedFile.language.toUpperCase()}</span>
                      </div>
                      
                      <div className="flex-1 overflow-hidden">
                        <Editor
                          height="100%"
                          language={selectedFile.language}
                          value={selectedFile.content}
                          theme="vs-dark"
                          options={{
                            readOnly: true,
                            minimap: { enabled: window.innerWidth > 1024 },
                            fontSize: 14,
                            lineNumbers: 'on',
                            scrollBeyondLastLine: false,
                            automaticLayout: true,
                            tabSize: 2,
                            wordWrap: 'on',
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
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-500">
              <div className="text-center p-8">
                <Code size={64} className="mx-auto mb-4 opacity-20" />
                <h3 className="text-lg font-semibold text-gray-400 mb-2">
                  No Code Yet
                </h3>
                <p className="text-sm text-gray-500 max-w-md">
                  Start chatting to generate your application. I'll propose features, you approve, and I'll generate the complete codebase!
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ChatApp;

