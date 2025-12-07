import React, { useState, useRef, useEffect, useCallback } from 'react';
import Editor from '@monaco-editor/react';
import { 
  Send, Code, CheckCircle, Loader2,
  FolderTree, FileCode, ChevronRight, ChevronDown,
  Sparkles, Bot, User, Rocket, ExternalLink,
  RefreshCw, Square, Globe, Terminal, Eye, MonitorPlay,
  Zap, AlertCircle, Maximize2, Activity, Cpu, FlaskConical,
  BarChart3, Users, Layers, DollarSign
} from 'lucide-react';

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

interface AppExecutionState {
  status: 'idle' | 'starting' | 'running' | 'stopped' | 'error';
  url: string | null;
  port: number | null;
  logs: string[];
  error: string | null;
  projectPath: string | null;
  fixesApplied: string[];
}

interface AgentInfo {
  id: string;
  name: string;
  icon: string;
  phase: string;
  description: string;
  usage: {
    calls: number;
    tokens: number;
    cost?: number;
  };
}

interface UsageStats {
  total_calls: number;
  total_tokens: number;
  total_cost: number;
}

type ActiveTab = 'editor' | 'preview' | 'console' | 'agents';

const SYMPTOM_TRACKER_DESCRIPTION = `A software application that allows users to track and monitor their symptoms over time, enabling them to identify patterns and potential triggers. Users can log symptoms, severity, duration, and associated factors such as food, stress, or environment to gain insights into their health and make informed decisions.

## Functional Requirements:
1. User Authentication - Register and login functionality
2. Symptom Logging - Log symptoms with severity (1-10), duration, date/time
3. Associated Factors - Track food, stress levels, sleep, weather, medications
4. Pattern Analysis - Visualize symptom trends over time with charts
5. Trigger Detection - Identify correlations between factors and symptoms
6. Symptom History - View and search past symptom entries
7. Export Data - Download symptom data as CSV/PDF
8. Reminders - Set reminders to log symptoms
9. Dashboard - Overview of recent symptoms and insights
10. Notes - Add detailed notes to symptom entries`;

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
    projectPath: null,
    fixesApplied: []
  });
  
  const [activeTab, setActiveTab] = useState<ActiveTab>('editor');
  const [showExecuteButton, setShowExecuteButton] = useState(false);
  const [previewWindow, setPreviewWindow] = useState<Window | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);
  
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [usageStats, setUsageStats] = useState<UsageStats>({ total_calls: 0, total_tokens: 0, total_cost: 0 });
  const [activeAgentPhase, setActiveAgentPhase] = useState<string>('');
  const [testCount, setTestCount] = useState<number>(0);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const codeScrollRef = useRef<HTMLDivElement>(null);
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
  const chatInputRef = useRef<HTMLTextAreaElement>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchAgents();
  }, []);

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

  const fetchAgents = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/agents`);
      const data = await response.json();
      setAgents(data.agents || []);
      if (data.total_usage) {
        setUsageStats(data.total_usage);
      }
    } catch (error) {
      console.error('Failed to fetch agents:', error);
    }
  };

  const fetchUsage = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/usage`);
      const data = await response.json();
      setUsageStats({
        total_calls: data.total_calls || 0,
        total_tokens: data.total_tokens || 0,
        total_cost: data.total_cost || 0
      });
    } catch (error) {
      console.error('Failed to fetch usage:', error);
    }
  };

  const loadSymptomTrackerPreset = () => {
    setInputMessage(SYMPTOM_TRACKER_DESCRIPTION);
    chatInputRef.current?.focus();
  };

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
      logs: ['🚀 Starting application with auto-fix enabled...'],
      error: null,
      fixesApplied: []
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
                
              case 'fix_applied':
                setAppExecution(prev => ({
                  ...prev,
                  logs: [...prev.logs, data.message],
                  fixesApplied: [...prev.fixesApplied, ...(data.fixes || [])]
                }));
                if (data.root_cause) {
                  setAppExecution(prev => ({
                    ...prev,
                    logs: [...prev.logs, `   📋 Root cause: ${data.root_cause}`]
                  }));
                }
                break;
                
              case 'files_updated':
                if (data.files && Array.isArray(data.files)) {
                  setCodeFiles(data.files);
                  if (selectedFile) {
                    const updatedFile = data.files.find((f: CodeFile) => f.filepath === selectedFile.filepath);
                    if (updatedFile) {
                      setSelectedFile(updatedFile);
                    }
                  }
                }
                setAppExecution(prev => ({
                  ...prev,
                  logs: [...prev.logs, `📝 Files updated with fixes`]
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
                if (data.files && Array.isArray(data.files)) {
                  setCodeFiles(data.files);
                }
                setActiveTab('preview');
                break;
                
              case 'error':
                setAppExecution(prev => ({
                  ...prev,
                  status: 'error',
                  error: data.message,
                  logs: [...prev.logs, `❌ Error: ${data.message}`]
                }));
                if (data.error_history && Array.isArray(data.error_history)) {
                  data.error_history.forEach((err: string) => {
                    setAppExecution(prev => ({
                      ...prev,
                      logs: [...prev.logs, `   └─ ${err.substring(0, 100)}...`]
                    }));
                  });
                }
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
  }, [codeFiles, conversationId, selectedFile]);

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
    setTestCount(0);

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
                setActiveAgentPhase(data.data.phase || '');
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
                const isTestFile = file.filepath?.includes('test') || file.test_type;
                const fileMsg = isTestFile
                  ? `\n🧪 Generated test: \`${file.filename}\`\n`
                  : `\n✅ Generated: \`${file.filename}\`\n`;
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

              case 'tests_generated':
                const testData = data.data;
                setTestCount(testData.test_count || 0);
                assistantMessage += `\n🧪 ${testData.message}\n`;
                setMessages(prev => prev.map(msg => 
                  msg.id === streamingMessageId 
                    ? { ...msg, content: assistantMessage }
                    : msg
                ));
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
                if (data.data.usage) {
                  setUsageStats({
                    total_calls: data.data.usage.total_calls || 0,
                    total_tokens: data.data.usage.total_tokens || 0,
                    total_cost: data.data.usage.total_cost || 0
                  });
                }
                setMessages(prev => prev.map(msg => 
                  msg.id === streamingMessageId 
                    ? { ...msg, content: assistantMessage }
                    : msg
                ));
                setIsGenerationComplete(true);
                setActiveAgentPhase('');
                fetchAgents();
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
    const isTestFile = node.name.includes('test') || node.name.includes('spec');

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
        {isTestFile ? (
          <FlaskConical size={14} className="text-emerald-400" />
        ) : (
          <FileCode size={14} className="text-gray-400" />
        )}
        <span className={`text-xs truncate ${isTestFile ? 'text-emerald-300' : 'text-gray-300'}`}>
          {node.name}
        </span>
      </div>
    );
  };

  const tree = codeFiles.length > 0 ? buildTree(codeFiles) : null;

  const downloadSourceCode = useCallback(async () => {
    if (codeFiles.length === 0) {
      console.warn('No files to download');
      return;
    }
    
    setIsDownloading(true);
    try {
      console.log(`Downloading ${codeFiles.length} files...`);
      
      const response = await fetch(`${API_URL}/api/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          files: codeFiles.map(f => ({
            filepath: f.filepath,
            content: f.content
          }))
        })
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Download failed: ${response.status} - ${errorText}`);
      }
      
      const blob = await response.blob();
      
      if (blob.size === 0) {
        throw new Error('Downloaded file is empty');
      }
      
      console.log(`Downloaded blob size: ${blob.size} bytes`);
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.style.display = 'none';
      
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = 'source-code.zip';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch) filename = filenameMatch[1];
      }
      
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }, 100);
      
      console.log(`Download initiated: ${filename}`);
    } catch (error) {
      console.error('Download error:', error);
      alert(`Download failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsDownloading(false);
    }
  }, [codeFiles]);

  const renderAgentsPanel = () => {
    const getPhaseIcon = (phase: string) => {
      switch (phase) {
        case 'planning': return '💡';
        case 'discovery': return '🏗️';
        case 'design': return '📋';
        case 'implementation': return '⚙️';
        case 'validation': return '🔍';
        case 'testing': return '🧪';
        case 'execution': return '🚀';
        default: return '🤖';
      }
    };

    return (
      <div className="flex-1 flex flex-col bg-gray-900 p-4 overflow-y-auto">
        <div className="mb-6">
          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <Users size={20} className="text-cyan-400" />
            Multi-Agent System
          </h3>
          <p className="text-sm text-gray-400 mb-4">
            Agents communicate via Model Context Protocol (MCP) for coordinated code generation.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center gap-2 mb-2">
              <Activity size={16} className="text-emerald-400" />
              <span className="text-sm font-semibold text-white">API Calls</span>
            </div>
            <div className="text-2xl font-bold text-emerald-400">{usageStats.total_calls}</div>
          </div>
          
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center gap-2 mb-2">
              <Cpu size={16} className="text-blue-400" />
              <span className="text-sm font-semibold text-white">Total Tokens</span>
            </div>
            <div className="text-2xl font-bold text-blue-400">{usageStats.total_tokens.toLocaleString()}</div>
          </div>
          
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign size={16} className="text-yellow-400" />
              <span className="text-sm font-semibold text-white">Estimated Cost</span>
            </div>
            <div className="text-2xl font-bold text-yellow-400">${usageStats.total_cost.toFixed(4)}</div>
          </div>
          
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center gap-2 mb-2">
              <FlaskConical size={16} className="text-violet-400" />
              <span className="text-sm font-semibold text-white">Test Files</span>
            </div>
            <div className="text-2xl font-bold text-violet-400">{testCount}</div>
          </div>
        </div>

        <h4 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
          <Layers size={14} />
          AGENT PIPELINE
        </h4>
        
        <div className="space-y-2">
          {agents.map((agent, index) => {
            const isActive = activeAgentPhase === agent.phase;
            return (
              <div
                key={agent.id}
                className={`bg-gray-800 rounded-lg p-3 border transition-all ${
                  isActive 
                    ? 'border-cyan-500 shadow-lg shadow-cyan-500/20' 
                    : 'border-gray-700 hover:border-gray-600'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{agent.icon || getPhaseIcon(agent.phase)}</span>
                    <div>
                      <div className="text-sm font-medium text-white flex items-center gap-2">
                        {agent.name}
                        {isActive && (
                          <Loader2 size={14} className="animate-spin text-cyan-400" />
                        )}
                      </div>
                      <div className="text-xs text-gray-500">{agent.description}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-gray-400">
                      {agent.usage?.calls || 0} calls
                    </div>
                    <div className="text-xs text-gray-500">
                      {(agent.usage?.tokens || 0).toLocaleString()} tokens
                    </div>
                  </div>
                </div>
                {index < agents.length - 1 && (
                  <div className="flex justify-center mt-2">
                    <ChevronDown size={14} className="text-gray-600" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

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
      case 'agents':
        return renderAgentsPanel();

      case 'preview':
        return (
          <div className="flex-1 flex flex-col bg-gray-900">
            {appExecution.status === 'running' && appExecution.url ? (
              <>
                <div className="bg-gray-800 border-b border-gray-700 px-4 py-2 flex items-center justify-between shrink-0">
                  <div className="flex items-center gap-3">
                    <div className="flex gap-1.5">
                      <div className="w-3 h-3 rounded-full bg-red-500 cursor-pointer" onClick={stopApplication} title="Stop" />
                      <div className="w-3 h-3 rounded-full bg-yellow-500" />
                      <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse" />
                    </div>
                    <div className="flex items-center gap-2 bg-gray-700 rounded-lg px-3 py-1.5">
                      <Globe size={14} className="text-green-400" />
                      <span className="text-sm text-gray-300 font-mono">{appExecution.url}</span>
                    </div>
                    {appExecution.fixesApplied.length > 0 && (
                      <span className="badge-purple text-xs flex items-center gap-1">
                        <Zap size={12} />
                        {appExecution.fixesApplied.length} fixes applied
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        const iframe = document.getElementById('preview-iframe') as HTMLIFrameElement;
                        if (iframe) iframe.src = iframe.src;
                      }}
                      className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
                      title="Refresh preview"
                    >
                      <RefreshCw size={16} className="text-gray-400 hover:text-white" />
                    </button>
                    <button
                      onClick={openPreviewWindow}
                      className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
                      title="Open in new window"
                    >
                      <Maximize2 size={16} className="text-gray-400 hover:text-white" />
                    </button>
                    <a
                      href={appExecution.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
                      title="Open in browser tab"
                    >
                      <ExternalLink size={16} className="text-gray-400 hover:text-white" />
                    </a>
                    <button
                      onClick={stopApplication}
                      className="p-2 hover:bg-red-600/20 rounded-lg transition-colors"
                      title="Stop application"
                    >
                      <Square size={16} className="text-red-400 hover:text-red-300" />
                    </button>
                  </div>
                </div>
                
                <div className="flex-1 bg-white relative">
                  <iframe
                    id="preview-iframe"
                    src={appExecution.url}
                    className="w-full h-full border-0"
                    title="Application Preview"
                    sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
                  />
                  <div className="absolute inset-0 flex items-center justify-center bg-gray-900/90 opacity-0 hover:opacity-100 transition-opacity pointer-events-none">
                    <div className="text-center pointer-events-auto">
                      <p className="text-gray-400 text-sm mb-3">Preview not loading?</p>
                      <a
                        href={appExecution.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-primary inline-flex items-center gap-2"
                      >
                        <ExternalLink size={16} />
                        Open in New Tab
                      </a>
                    </div>
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
                      <p className="text-sm text-gray-400 mb-4">Installing dependencies and starting the server</p>
                      {appExecution.fixesApplied.length > 0 && (
                        <div className="bg-violet-500/20 border border-violet-500/30 rounded-lg p-3 max-w-md mx-auto">
                          <p className="text-violet-300 text-sm flex items-center gap-2 justify-center">
                            <Zap size={16} />
                            Auto-fixed {appExecution.fixesApplied.length} issue(s)
                          </p>
                        </div>
                      )}
                    </>
                  ) : appExecution.status === 'error' ? (
                    <>
                      <AlertCircle size={48} className="mx-auto mb-4 text-red-400" />
                      <h3 className="text-lg font-semibold text-white mb-2">Failed to Start</h3>
                      <p className="text-sm text-red-400 max-w-md mb-4">{appExecution.error}</p>
                      {appExecution.fixesApplied.length > 0 && (
                        <p className="text-sm text-gray-400 mb-4">
                          Tried {appExecution.fixesApplied.length} automatic fix(es) but couldn't resolve all issues.
                        </p>
                      )}
                      <button
                        onClick={executeApplication}
                        className="mt-2 btn-primary flex items-center gap-2 mx-auto"
                      >
                        <RefreshCw size={16} />
                        Retry with Auto-Fix
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
                    log.includes('🔧') ? 'text-violet-400 font-medium' :
                    log.includes('📋') ? 'text-violet-300 pl-4' :
                    log.includes('📝') ? 'text-teal-400' :
                    log.includes('⚠️') ? 'text-orange-400' :
                    log.includes('└─') ? 'text-gray-500 text-xs pl-4' :
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
                    {selectedFile.filepath.includes('test') ? (
                      <FlaskConical size={16} className="text-emerald-400" />
                    ) : (
                      <Code size={16} className="text-violet-400" />
                    )}
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
                  AI Code Generator
                </h1>
                <p className="text-xs text-gray-400">
                  Multi-Agent System with MCP Integration
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {usageStats.total_calls > 0 && (
                <span className="badge-cyan text-xs flex items-center gap-1">
                  <Activity size={12} />
                  {usageStats.total_calls} API calls
                </span>
              )}
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
        <div className="w-full md:w-[35%] lg:w-[30%] glass-dark border-r border-gray-700/50 flex flex-col min-h-0">
          <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0 scrollbar scrollbar-w-3 scrollbar-thumb-cyan-500 scrollbar-track-gray-800/50 hover:scrollbar-thumb-cyan-400">
            {messages.length === 0 && (
              <div className="text-center py-8">
                <Bot size={40} className="mx-auto mb-3 text-cyan-400 opacity-50" />
                <h3 className="text-base font-semibold text-white mb-2">
                  Let's Build Something Amazing!
                </h3>
                <p className="text-sm text-gray-400 px-4 mb-4">
                  Describe your application idea, and our multi-agent system will help you build it.
                </p>
                
                <button
                  onClick={loadSymptomTrackerPreset}
                  className="mt-4 px-4 py-2 bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/30 rounded-lg text-sm text-emerald-300 transition-all flex items-center gap-2 mx-auto"
                >
                  <Zap size={14} />
                  Try: Symptom Tracker App
                </button>
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
                      </div>
                    </div>
                  </div>
                ))}
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
                <button
                  onClick={() => { setActiveTab('agents'); fetchAgents(); }}
                  className={activeTab === 'agents' ? 'tab-active' : 'tab-inactive'}
                >
                  <div className="flex items-center gap-2">
                    <BarChart3 size={14} />
                    <span>Agents</span>
                    {usageStats.total_calls > 0 && (
                      <span className="text-[10px] badge bg-cyan-600 text-white">
                        {usageStats.total_calls}
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
                <p className="text-sm text-gray-500 max-w-md mb-6">
                  Start chatting to generate your application!
                </p>
                
                <button
                  onClick={loadSymptomTrackerPreset}
                  className="px-4 py-2 bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/30 rounded-lg text-sm text-emerald-300 transition-all flex items-center gap-2 mx-auto"
                >
                  <Zap size={14} />
                  Try Demo: Symptom Tracker App
                </button>
              </div>
            </div>
          )}
        </div>

        {renderExecuteButton()}
      </div>
    </div>
  );
}

export default ChatApp;
