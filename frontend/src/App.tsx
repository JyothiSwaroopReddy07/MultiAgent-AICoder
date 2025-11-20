// Main App - Chat-based Code Generation Interface
import ChatApp from './ChatApp';

export default ChatApp;

/* 
// OLD ONE-SHOT GENERATION INTERFACE (commented out - use ChatApp instead)
import React, { useState, useRef, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import { 
  Play, FolderTree, Terminal, Activity, 
  FileCode, CheckCircle, AlertCircle, Loader2,
  X, ChevronRight, ChevronDown, Download
} from 'lucide-react';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8500';

interface FileNode {
  name: string;
  type: 'file' | 'folder';
  path: string;
  children?: FileNode[];
  content?: string;
  language?: string;
}

interface CodeFile {
  filename: string;
  filepath: string;
  content: string;
  language: string;
}

interface ActivityLog {
  id: string;
  type: 'phase' | 'agent' | 'file' | 'error' | 'success';
  message: string;
  timestamp: Date;
  data?: any;
}

function App() {
  const [description, setDescription] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [selectedDatabase, setSelectedDatabase] = useState<'auto' | 'postgresql' | 'mongodb'>('auto');
  const [files, setFiles] = useState<CodeFile[]>([]);
  const [openFiles, setOpenFiles] = useState<CodeFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<CodeFile | null>(null);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['root']));
  const [activityLogs, setActivityLogs] = useState<ActivityLog[]>([]);
  const [currentPhase, setCurrentPhase] = useState('');
  const [currentAgent, setCurrentAgent] = useState('');
  const [progress, setProgress] = useState(0);
  
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
  const activityEndRef = useRef<HTMLDivElement>(null);
  const isGeneratingRef = useRef<boolean>(false);

  // Cleanup stream on unmount
  useEffect(() => {
    return () => {
      if (readerRef.current) {
        readerRef.current.cancel().catch(console.error);
        readerRef.current = null;
      }
    };
  }, []);

  // Auto-scroll activity logs
  useEffect(() => {
    activityEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activityLogs]);

  const addActivityLog = (type: ActivityLog['type'], message: string, data?: any) => {
    const log: ActivityLog = {
      id: Date.now().toString(),
      type,
      message,
      timestamp: new Date(),
      data
    };
    setActivityLogs(prev => [...prev, log]);
  };

  const handleGenerate = async () => {
    if (!description.trim() || isGeneratingRef.current) return;

    isGeneratingRef.current = true;
    setIsGenerating(true);
    setFiles([]);
    setOpenFiles([]);
    setSelectedFile(null);
    setActivityLogs([]);
    setProgress(0);
    
    addActivityLog('phase', '[START] Starting code generation...', {});

    try {
      // First, initiate the generation with POST
      const response = await fetch(`${API_URL}/api/v2/generate/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
        description,
          language: 'nextjs',
          database: selectedDatabase,
          requirements: []
        })
      });

      if (!response.ok) {
        throw new Error('Failed to start generation');
      }

      // Read the SSE stream
      const reader = response.body?.getReader();
      readerRef.current = reader || null;
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response body');
      }

      const readStream = async () => {
        let buffer = '';
        
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) {
            setIsGenerating(false);
            isGeneratingRef.current = false;
            readerRef.current = null;
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          
          // Keep last incomplete line in buffer
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                handleStreamEvent(data);
              } catch (e) {
                console.error('Failed to parse event:', e, line);
              }
            }
          }
        }
      };

      readStream().catch(error => {
        console.error('Stream reading error:', error);
        addActivityLog('error', '[ERROR] Connection error occurred', {});
        setIsGenerating(false);
        isGeneratingRef.current = false;
        readerRef.current = null;
      });

    } catch (error) {
      console.error('Generation failed:', error);
      addActivityLog('error', '[ERROR] Failed to generate code. Please try again.', {});
      setIsGenerating(false);
      isGeneratingRef.current = false;
      // Ensure stream is cleaned up
      if (readerRef.current) {
        readerRef.current.cancel().catch(console.error);
        readerRef.current = null;
      }
    }
  };

  const handleStreamEvent = (event: any) => {
    switch (event.type) {
      case 'started':
        addActivityLog('success', '[OK] Generation started', { request_id: event.request_id });
        setProgress(5);
        break;

      case 'phase_started':
        setCurrentPhase(event.phase);
        addActivityLog('phase', `[PHASE] ${event.phase}`, {});
        
        // Calculate progress dynamically based on phase number
        const phases = [
          'Phase 1: Discovery & Analysis',
          'Phase 2: Design & Planning',
          'Phase 3: Implementation',
          'Phase 4: Quality Assurance',
          'Phase 5: Validation',
          'Phase 6: Monitoring'
        ];
        const phaseIndex = phases.findIndex(p => p === event.phase);
        const calculatedProgress = phaseIndex >= 0 ? ((phaseIndex + 1) / phases.length) * 90 : 0;
        setProgress(calculatedProgress);
        break;

      case 'agent_started':
        setCurrentAgent(event.agent);
        addActivityLog('agent', `[AGENT] ${event.agent}: ${event.activity}`, {});
        break;

      case 'agent_completed':
        addActivityLog('success', `[OK] ${event.agent} completed`, event.data);
        setCurrentAgent('');
        break;

      case 'file_generated':
        const newFile: CodeFile = event.file;
        setFiles(prev => {
          const updated = [...prev, newFile];
          return updated;
        });
        
        // Auto-open first file only if nothing is selected
        setSelectedFile(current => {
          if (!current && files.length === 0) {
            setOpenFiles([newFile]);
            return newFile;
          }
          return current;
        });
        
        addActivityLog('file', `[FILE] Generated ${newFile.filename}`, {});
        break;

      case 'completed':
        addActivityLog('success', '[SUCCESS] Code generation completed!', event.data);
        setIsGenerating(false);
        isGeneratingRef.current = false;
        setProgress(100);
        setCurrentPhase('');
        setCurrentAgent('');
        if (readerRef.current) {
          readerRef.current.cancel().catch(console.error);
          readerRef.current = null;
        }
        break;

      case 'error':
        addActivityLog('error', `[ERROR] Error: ${event.error}`, {});
        setIsGenerating(false);
        isGeneratingRef.current = false;
        if (readerRef.current) {
          readerRef.current.cancel().catch(console.error);
          readerRef.current = null;
        }
        break;
    }
  };

  const cancelGeneration = () => {
    if (readerRef.current) {
      readerRef.current.cancel().catch(console.error);
      readerRef.current = null;
    }
    setIsGenerating(false);
    isGeneratingRef.current = false;
    addActivityLog('error', '[WARN] Generation cancelled', {});
  };

  // Build folder tree from flat file list
  const buildTree = (files: CodeFile[]): FileNode => {
    const root: FileNode = {
      name: 'Generated Project',
      type: 'folder',
      path: 'root',
      children: []
    };

    files.forEach(file => {
      const parts = file.filepath.split('/').filter(part => part.trim() !== '');
      let currentNode = root;

      parts.forEach((part: string, index: number) => {
        const isLast = index === parts.length - 1;
        const path = parts.slice(0, index + 1).join('/');

        if (!currentNode.children) currentNode.children = [];

        let existingNode = currentNode.children.find(child => child.name === part);

        if (!existingNode) {
          existingNode = {
            name: part,
            type: isLast ? 'file' : 'folder',
            path: path,
            language: isLast ? file.language : undefined,
            content: isLast ? file.content : undefined,
            children: isLast ? undefined : []
          };
          currentNode.children.push(existingNode);
        }

        if (!isLast) currentNode = existingNode;
      });
    });

    return root;
  };

  const toggleFolder = (path: string) => {
    const newExpanded = new Set(expandedFolders);
    if (newExpanded.has(path)) {
      newExpanded.delete(path);
    } else {
      newExpanded.add(path);
    }
    setExpandedFolders(newExpanded);
  };

  const openFile = (file: CodeFile) => {
    setSelectedFile(file);
    if (!openFiles.find(f => f.filepath === file.filepath)) {
      setOpenFiles([...openFiles, file]);
    }
  };

  const closeFile = (file: CodeFile) => {
    setOpenFiles(prev => {
      const newOpenFiles = prev.filter(f => f.filepath !== file.filepath);
      
      // Update selected file if closing the currently selected one
      setSelectedFile(current => {
        if (current?.filepath === file.filepath) {
          return newOpenFiles[newOpenFiles.length - 1] || null;
        }
        return current;
      });
      
      return newOpenFiles;
    });
  };

  const getFileIcon = (name: string) => {
    const parts = name.split('.');
    
    // Special file names
    if (name === 'package.json') return '[PKG]';
    if (name === 'tsconfig.json') return '[CFG]';
    if (name === 'next.config.js' || name === 'next.config.ts') return '[CFG]';
    if (name === 'tailwind.config.js' || name === 'tailwind.config.ts') return '[CFG]';
    if (name === 'Dockerfile') return '[DOC]';
    if (name === 'docker-compose.yml') return '[DOC]';
    if (name === '.env' || name === '.env.local' || name === '.env.example') return '[ENV]';
    if (name === 'README.md') return '[MD]';
    if (parts.length === 1) return '[F]';
    
    const ext = parts.pop()?.toLowerCase();
    const icons: { [key: string]: string } = {
      tsx: '[TSX]',
      jsx: '[JSX]',
      ts: '[TS]',
      js: '[JS]',
      html: '[HTML]',
      css: '[CSS]',
      scss: '[SCSS]',
      json: '[JSON]',
      md: '[MD]',
      yml: '[YML]',
      yaml: '[YML]',
      txt: '[TXT]',
      sql: '[SQL]',
      sh: '[SH]',
      env: '[ENV]',
      prisma: '[PRI]',
      gitignore: '[GIT]'
    };
    return icons[ext || ''] || '[F]';
  };

  const getLanguageMode = (language: string): string => {
    const langMap: { [key: string]: string } = {
      nextjs: 'typescript',
      typescript: 'typescript',
      javascript: 'javascript',
      tsx: 'typescript',
      jsx: 'javascript',
      html: 'html',
      css: 'css',
      scss: 'scss',
      json: 'json',
      yaml: 'yaml',
      yml: 'yaml',
      markdown: 'markdown',
      md: 'markdown',
      sql: 'sql',
      dockerfile: 'dockerfile',
      shell: 'shell',
      sh: 'shell',
      env: 'shell'
    };
    return langMap[language.toLowerCase()] || 'typescript'; // Default to TypeScript for Next.js
  };

  const downloadAllFiles = () => {
    files.forEach(file => {
      const blob = new Blob([file.content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.filename;
      a.click();
      URL.revokeObjectURL(url);
    });
  };

  const renderTreeNode = (node: FileNode, depth: number = 0): React.ReactNode => {
    const isExpanded = expandedFolders.has(node.path);
    const isSelected = selectedFile?.filepath === node.path;

    if (node.type === 'folder') {
      return (
        <div key={node.path} className="animate-in">
          <div
            className={`flex items-center gap-2 px-2 py-1.5 cursor-pointer transition-colors group ${
              isSelected ? 'bg-gray-700/50' : 'hover:bg-gray-700/30'
            }`}
            style={{ paddingLeft: `${depth * 12 + 8}px` }}
            onClick={() => toggleFolder(node.path)}
          >
            {isExpanded ? (
              <ChevronDown size={14} className="text-gray-400 group-hover:text-blue-400 transition-colors" />
            ) : (
              <ChevronRight size={14} className="text-gray-400 group-hover:text-blue-400 transition-colors" />
            )}
            <FolderTree size={14} className="text-blue-400 flex-shrink-0" />
            <span className="text-xs md:text-sm text-gray-200 truncate flex-1">{node.name}</span>
            {node.children && (
              <span className="ml-auto text-xs text-gray-500 bg-gray-700/50 px-1.5 py-0.5 rounded-full flex-shrink-0">
                {node.children.length}
              </span>
            )}
          </div>
          {isExpanded && node.children && (
            <div className="animate-in">
              {node.children.map(child => renderTreeNode(child, depth + 1))}
            </div>
          )}
        </div>
      );
    }

    // File node
    const file = files.find(f => f.filepath === node.path);
    return (
      <div
        key={node.path}
        className={`flex items-center gap-2 px-2 py-1.5 cursor-pointer transition-all group ${
          isSelected 
            ? 'bg-blue-600/30 border-l-2 border-blue-500 text-white' 
            : 'hover:bg-gray-700/30 text-gray-300'
        }`}
        style={{ paddingLeft: `${depth * 12 + 24}px` }}
        onClick={() => file && openFile(file)}
      >
        <span className="text-xs font-mono flex-shrink-0 group-hover:text-blue-400 transition-colors">
          {getFileIcon(node.name)}
        </span>
        <span className="text-xs md:text-sm truncate flex-1">{node.name}</span>
      </div>
    );
  };

  const tree = files.length > 0 ? buildTree(files) : null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex flex-col">
      {/* Header */}
      <div className="glass border-b border-gray-700/50 shadow-xl sticky top-0 z-50">
        <div className="px-4 md:px-6 py-4">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex-1 min-w-0">
              <h1 className="text-xl md:text-2xl font-bold text-white flex items-center gap-2 animate-in">
                <Terminal className="text-blue-400 flex-shrink-0" size={24} />
                <span className="truncate">AI Next.js Full-Stack Generator</span>
              </h1>
              <p className="text-gray-400 text-xs md:text-sm mt-1">
                Describe your app - Get complete Next.js + Database + Docker setup in minutes
              </p>
            </div>
            {files.length > 0 && (
              <button
                onClick={downloadAllFiles}
                className="btn-success flex items-center gap-2 shadow-lg"
              >
                <Download size={16} />
                <span className="hidden sm:inline">Download All</span>
              </button>
            )}
          </div>
        </div>

        {/* Progress Bar */}
        {isGenerating && (
          <div className="px-4 md:px-6 pb-4 animate-in">
            <div className="bg-gray-700/50 rounded-full h-2.5 overflow-hidden shadow-inner">
              <div
                className="bg-gradient-to-r from-blue-500 via-blue-400 to-cyan-500 h-full transition-all duration-500 ease-out shadow-glow-blue"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="flex flex-wrap justify-between items-center mt-3 gap-2">
              <div className="text-xs md:text-sm text-gray-400 flex items-center gap-2">
                {currentPhase && (
                  <span className="badge-blue font-semibold animate-pulse">
                    {currentPhase}
                  </span>
                )}
                {currentAgent && (
                  <span className="hidden md:inline">
                    {currentAgent}
                  </span>
                )}
              </div>
              <button
                onClick={cancelGeneration}
                className="text-red-400 hover:text-red-300 text-xs md:text-sm flex items-center gap-1 transition-colors"
              >
                <X size={14} />
                <span>Cancel</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
        {/* Sidebar - Input or File Tree */}
        <div className="w-full md:w-80 lg:w-96 glass-dark border-b md:border-b-0 md:border-r border-gray-700/50 flex flex-col">
          {files.length === 0 ? (
            /* Input Section */
            <div className="p-4 md:p-6 flex flex-col h-full">
              <h2 className="text-base md:text-lg font-semibold text-white mb-3 md:mb-4 flex items-center gap-2">
                <Activity className="text-blue-400" size={20} />
                What do you want to build?
              </h2>
          
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
                placeholder="Example: Build a task management app with user authentication, teams, projects, and real-time notifications..."
                className="input flex-1 resize-none mb-4 text-sm md:text-base min-h-[120px] md:min-h-[200px]"
            disabled={isGenerating}
          />

              {/* Tech Stack Display */}
              <div className="card mb-4 animate-in">
                <div className="text-xs md:text-sm font-semibold text-gray-200 mb-3 flex items-center gap-2">
                  <CheckCircle className="text-green-400 flex-shrink-0" size={16} />
                  Tech Stack (Fixed)
                </div>
                <div className="space-y-2 text-xs md:text-sm text-gray-400">
                  <div className="flex items-start gap-2">
                    <span className="text-blue-400 mt-0.5">•</span>
                    <span><strong className="text-gray-300">Frontend:</strong> Next.js 14 + TypeScript + Tailwind CSS</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-green-400 mt-0.5">•</span>
                    <span><strong className="text-gray-300">Backend:</strong> Next.js API Routes (REST)</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-purple-400 mt-0.5">•</span>
                    <span><strong className="text-gray-300">Database:</strong> PostgreSQL / MongoDB (auto-selected)</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-cyan-400 mt-0.5">•</span>
                    <span><strong className="text-gray-300">Deployment:</strong> Docker + docker-compose</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-yellow-400 mt-0.5">•</span>
                    <span><strong className="text-gray-300">Testing:</strong> Jest + React Testing Library</span>
                  </div>
                </div>
              </div>

              {/* Optional Database Selection */}
              <div className="mb-4">
                <label className="block text-xs md:text-sm font-medium text-gray-300 mb-2">
                  Database Preference (Optional)
              </label>
              <select
                  value={selectedDatabase}
                  onChange={(e) => setSelectedDatabase(e.target.value as 'auto' | 'postgresql' | 'mongodb')}
                  className="input w-full text-sm"
                disabled={isGenerating}
              >
                  <option value="auto">Auto-select (Recommended)</option>
                  <option value="postgresql">PostgreSQL (Relational)</option>
                  <option value="mongodb">MongoDB (Document)</option>
              </select>
                <p className="text-xs text-gray-500 mt-2">
                  AI will automatically choose the best database for your use case
                </p>
            </div>

            <button
              onClick={handleGenerate}
              disabled={isGenerating || !description.trim()}
                className="btn-primary w-full py-3 text-sm md:text-base font-semibold shadow-glow-blue"
            >
                {isGenerating ? (
                  <>
                    <Loader2 className="animate-spin" size={18} />
                    <span className="hidden sm:inline">Generating Full-Stack App...</span>
                    <span className="sm:hidden">Generating...</span>
                  </>
                ) : (
                  <>
                    <Play size={18} />
                    <span className="hidden sm:inline">Generate Next.js App</span>
                    <span className="sm:hidden">Generate</span>
                  </>
                )}
            </button>
          </div>
          ) : (
            /* File Tree */
            <div className="flex flex-col h-full animate-in">
              <div className="px-3 md:px-4 py-3 border-b border-gray-700/50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-gray-400 text-xs font-semibold tracking-wider">
                    <FolderTree size={16} className="text-blue-400" />
                    <span>EXPLORER</span>
                  </div>
                  <span className="badge-blue text-xs">{files.length}</span>
                </div>
              </div>
              <div className="flex-1 overflow-y-auto">
                {tree && tree.children && tree.children.map(child => renderTreeNode(child, 0))}
              </div>
            </div>
          )}
            </div>

        {/* Main Editor Area */}
        <div className="flex-1 flex flex-col bg-editor-bg overflow-hidden">
          {selectedFile ? (
            <>
              {/* File Tabs */}
              <div className="bg-editor-sidebar border-b border-editor-border flex items-center px-2 gap-1 overflow-x-auto scrollbar-thin">
                {openFiles.map(file => (
                  <div
                    key={file.filepath}
                    className={`flex items-center gap-2 px-3 py-2 cursor-pointer group transition-all flex-shrink-0 ${
                      selectedFile.filepath === file.filepath
                        ? 'bg-editor-bg text-white border-t-2 border-blue-500'
                        : 'text-gray-400 hover:text-white hover:bg-editor-hover'
                    }`}
                    onClick={() => setSelectedFile(file)}
                  >
                    <span className="text-xs font-mono">{getFileIcon(file.filename)}</span>
                    <span className="text-xs md:text-sm font-medium truncate max-w-[150px]">{file.filename}</span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        closeFile(file);
                      }}
                      className="opacity-0 group-hover:opacity-100 hover:text-red-400 transition-opacity flex-shrink-0"
                    >
                      <X size={14} />
                    </button>
                      </div>
                    ))}
                  </div>

              {/* Monaco Editor */}
              <div className="flex-1 overflow-hidden">
                <Editor
                  height="100%"
                  language={getLanguageMode(selectedFile.language)}
                  value={selectedFile.content}
                  theme="vs-dark"
                  options={{
                    readOnly: true,
                    minimap: { enabled: window.innerWidth > 768 },
                    fontSize: window.innerWidth < 640 ? 12 : 14,
                    lineNumbers: 'on',
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                    tabSize: 2,
                    wordWrap: 'on',
                    folding: true,
                    renderLineHighlight: 'line',
                  }}
                />
              </div>

              {/* Status Bar */}
              <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-3 md:px-4 py-2 flex gap-4 md:gap-6 text-xs text-white flex-wrap">
                <span className="flex items-center gap-1">
                  <span className="hidden sm:inline">Lines:</span>
                  {selectedFile.content.split('\n').length}
                </span>
                  <span className="flex items-center gap-1">
                    <span className="hidden sm:inline">Size:</span>
                  {(selectedFile.content.length / 1024).toFixed(1)} KB
                  </span>
                  <span className="flex items-center gap-1 font-semibold">
                  {selectedFile.language.toUpperCase()}
                  </span>
                </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-500 p-8">
              <div className="text-center animate-in">
                <FileCode size={64} className="mx-auto mb-4 opacity-20" />
                <p className="text-base md:text-lg font-medium mb-2">No file selected</p>
                <p className="text-xs md:text-sm text-gray-600">Select a file from the explorer to view its content</p>
              </div>
            </div>
          )}
        </div>

        {/* Activity Panel */}
        <div className="w-full md:w-80 lg:w-96 glass-dark border-t md:border-t-0 md:border-l border-gray-700/50 flex flex-col max-h-96 md:max-h-full">
          <div className="px-3 md:px-4 py-3 border-b border-gray-700/50 flex items-center justify-between sticky top-0 bg-gray-900/90 backdrop-blur-sm z-10">
            <div className="flex items-center gap-2">
              <Activity size={16} className="text-green-400 animate-pulse" />
              <span className="text-xs md:text-sm font-semibold text-white tracking-wider">ACTIVITY LOG</span>
            </div>
            <span className="badge-green text-xs">{activityLogs.length}</span>
          </div>
          
          <div className="flex-1 overflow-y-auto p-3 md:p-4 space-y-2 scrollbar-thin">
            {activityLogs.length === 0 ? (
              <div className="text-center text-gray-500 text-xs md:text-sm mt-8 p-4 animate-in">
                <Terminal size={32} className="mx-auto mb-3 opacity-30" />
                <p>No activity yet</p>
                <p className="text-xs text-gray-600 mt-1">Click "Generate" to start</p>
              </div>
            ) : (
              activityLogs.map(log => (
                <div
                  key={log.id}
                  className={`p-2 md:p-3 rounded-lg text-xs md:text-sm transition-all animate-in ${
                    log.type === 'phase'
                      ? 'bg-blue-500/20 border border-blue-500/30 text-blue-200 shadow-glow-blue'
                      : log.type === 'agent'
                      ? 'bg-purple-500/20 border border-purple-500/30 text-purple-200'
                      : log.type === 'file'
                      ? 'bg-green-500/20 border border-green-500/30 text-green-200'
                      : log.type === 'error'
                      ? 'bg-red-500/20 border border-red-500/30 text-red-200'
                      : 'bg-gray-700/50 border border-gray-600/30 text-gray-300'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    {log.type === 'phase' && <CheckCircle size={14} className="mt-0.5 flex-shrink-0" />}
                    {log.type === 'agent' && <Loader2 size={14} className="mt-0.5 animate-spin flex-shrink-0" />}
                    {log.type === 'file' && <FileCode size={14} className="mt-0.5 flex-shrink-0" />}
                    {log.type === 'error' && <AlertCircle size={14} className="mt-0.5 flex-shrink-0" />}
                    {log.type === 'success' && <CheckCircle size={14} className="mt-0.5 flex-shrink-0" />}
                    
                    <div className="flex-1 min-w-0">
                      <div className="font-medium break-words leading-relaxed">{log.message}</div>
                      <div className="text-xs opacity-60 mt-1 font-mono">
                        {log.timestamp.toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
          </div>
              ))
        )}
            <div ref={activityEndRef} className="h-4" />
          </div>
        </div>
      </div>
    </div>
  );
}

// export default App;
*/
