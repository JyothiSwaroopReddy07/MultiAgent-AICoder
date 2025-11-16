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
  const [language, setLanguage] = useState('python');
  const [isGenerating, setIsGenerating] = useState(false);
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
    if (!description.trim()) return;

    setIsGenerating(true);
    setFiles([]);
    setOpenFiles([]);
    setSelectedFile(null);
    setActivityLogs([]);
    setProgress(0);
    
    addActivityLog('phase', '🚀 Starting code generation...', {});

    try {
      // First, initiate the generation with POST
      const response = await fetch(`${API_URL}/api/v2/generate/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          description,
          language,
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
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) {
            setIsGenerating(false);
            readerRef.current = null;
            break;
          }

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');

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
        addActivityLog('error', '❌ Connection error occurred', {});
        setIsGenerating(false);
        readerRef.current = null;
      });

    } catch (error) {
      console.error('Generation failed:', error);
      addActivityLog('error', '❌ Failed to generate code. Please try again.', {});
      setIsGenerating(false);
    }
  };

  const handleStreamEvent = (event: any) => {
    switch (event.type) {
      case 'started':
        addActivityLog('success', '✅ Generation started', { request_id: event.request_id });
        setProgress(5);
        break;

      case 'phase_started':
        setCurrentPhase(event.phase);
        addActivityLog('phase', `📋 ${event.phase}`, {});
        const phaseProgress = {
          'Phase 1: Discovery & Analysis': 20,
          'Phase 2: Design & Planning': 40,
          'Phase 3: Implementation': 60,
          'Phase 4: Quality Assurance': 80,
          'Phase 5: Validation': 90,
        };
        setProgress(phaseProgress[event.phase as keyof typeof phaseProgress] || 0);
        break;

      case 'agent_started':
        setCurrentAgent(event.agent);
        addActivityLog('agent', `🤖 ${event.agent}: ${event.activity}`, {});
        break;

      case 'agent_completed':
        addActivityLog('success', `✓ ${event.agent} completed`, event.data);
        setCurrentAgent('');
        break;

      case 'file_generated':
        const newFile: CodeFile = event.file;
        setFiles(prev => {
          const updated = [...prev, newFile];
          // Auto-open first file
          if (updated.length === 1) {
            setSelectedFile(newFile);
            setOpenFiles([newFile]);
          }
          return updated;
        });
        addActivityLog('file', `📄 Generated ${newFile.filename}`, {});
        break;

      case 'completed':
        addActivityLog('success', '🎉 Code generation completed!', event.data);
        setIsGenerating(false);
        setProgress(100);
        setCurrentPhase('');
        setCurrentAgent('');
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
        }
        break;

      case 'error':
        addActivityLog('error', `❌ Error: ${event.error}`, {});
        setIsGenerating(false);
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
        }
        break;
    }
  };

  const cancelGeneration = () => {
    if (readerRef.current) {
      readerRef.current.cancel();
      readerRef.current = null;
    }
    setIsGenerating(false);
    addActivityLog('error', '⚠️ Generation cancelled', {});
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
      const parts = file.filepath.split('/');
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
    const newOpenFiles = openFiles.filter(f => f.filepath !== file.filepath);
    setOpenFiles(newOpenFiles);
    if (selectedFile?.filepath === file.filepath) {
      setSelectedFile(newOpenFiles[newOpenFiles.length - 1] || null);
    }
  };

  const getFileIcon = (name: string) => {
    const ext = name.split('.').pop()?.toLowerCase();
    const icons: { [key: string]: string } = {
      py: '🐍', js: '📜', ts: '📘', tsx: '⚛️', jsx: '⚛️',
      java: '☕', go: '🔵', rs: '🦀', html: '🌐', css: '🎨',
      json: '📋', md: '📝', yml: '⚙️', yaml: '⚙️', txt: '📄',
      sql: '🗄️', sh: '⚡', env: '🔐'
    };
    return icons[ext || ''] || '📄';
  };

  const getLanguageMode = (language: string): string => {
    const langMap: { [key: string]: string } = {
      python: 'python',
      javascript: 'javascript',
      typescript: 'typescript',
      java: 'java',
      go: 'go',
      rust: 'rust',
      html: 'html',
      css: 'css',
      json: 'json',
      yaml: 'yaml',
      markdown: 'markdown',
      sql: 'sql',
      shell: 'shell'
    };
    return langMap[language.toLowerCase()] || 'plaintext';
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
        <div key={node.path}>
          <div
            className={`flex items-center gap-2 px-2 py-1 cursor-pointer hover:bg-gray-700 ${
              isSelected ? 'bg-gray-700' : ''
            }`}
            style={{ paddingLeft: `${depth * 12 + 8}px` }}
            onClick={() => toggleFolder(node.path)}
          >
            {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            <FolderTree size={14} className="text-blue-400" />
            <span className="text-sm text-gray-200">{node.name}</span>
            {node.children && (
              <span className="ml-auto text-xs text-gray-500 bg-gray-700 px-2 rounded-full">
                {node.children.length}
              </span>
            )}
          </div>
          {isExpanded && node.children && (
            <div>
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
        className={`flex items-center gap-2 px-2 py-1 cursor-pointer hover:bg-gray-700 ${
          isSelected ? 'bg-blue-600/30 border-l-2 border-blue-500' : ''
        }`}
        style={{ paddingLeft: `${depth * 12 + 24}px` }}
        onClick={() => file && openFile(file)}
      >
        <FileCode size={14} className="text-gray-400" />
        <span className="text-sm text-gray-300">{node.name}</span>
      </div>
    );
  };

  const tree = files.length > 0 ? buildTree(files) : null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex flex-col">
      {/* Header */}
      <div className="bg-gray-800/50 backdrop-blur-lg border-b border-gray-700 shadow-xl">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                <Terminal className="text-blue-400" />
                AI Coder - No Code Required
              </h1>
              <p className="text-gray-400 text-sm">Describe what you want - Watch AI build it in real-time</p>
            </div>
            {files.length > 0 && (
              <button
                onClick={downloadAllFiles}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition"
              >
                <Download size={16} />
                Download All
              </button>
            )}
          </div>
        </div>

        {/* Progress Bar */}
        {isGenerating && (
          <div className="px-6 pb-4">
            <div className="bg-gray-700 rounded-full h-2 overflow-hidden">
              <div
                className="bg-gradient-to-r from-blue-500 to-cyan-500 h-full transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="flex justify-between items-center mt-2">
              <div className="text-sm text-gray-400">
                {currentPhase && <span className="font-semibold text-blue-400">{currentPhase}</span>}
                {currentAgent && <span className="ml-2">• {currentAgent}</span>}
              </div>
              <button
                onClick={cancelGeneration}
                className="text-red-400 hover:text-red-300 text-sm flex items-center gap-1"
              >
                <X size={14} />
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar - Input or File Tree */}
        <div className="w-80 bg-gray-800/80 border-r border-gray-700 flex flex-col">
          {files.length === 0 ? (
            /* Input Section */
            <div className="p-6 flex flex-col h-full">
              <h2 className="text-lg font-semibold text-white mb-4">What do you want to build?</h2>
              
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Example: Build a REST API for a todo app with user authentication, JWT tokens, and SQLite database..."
                className="flex-1 px-4 py-3 bg-gray-700 text-white border border-gray-600 rounded-lg focus:border-blue-500 focus:outline-none resize-none mb-4"
                disabled={isGenerating}
              />

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Programming Language
                </label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full px-4 py-2 bg-gray-700 text-white border border-gray-600 rounded-lg focus:border-blue-500 focus:outline-none"
                  disabled={isGenerating}
                >
                  <option value="python">Python</option>
                  <option value="javascript">JavaScript</option>
                  <option value="typescript">TypeScript</option>
                  <option value="java">Java</option>
                  <option value="go">Go</option>
                  <option value="rust">Rust</option>
                </select>
              </div>

              <button
                onClick={handleGenerate}
                disabled={isGenerating || !description.trim()}
                className="w-full px-6 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 text-white font-semibold rounded-lg hover:from-blue-700 hover:to-cyan-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg flex items-center justify-center gap-2"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="animate-spin" size={18} />
                    Generating...
                  </>
                ) : (
                  <>
                    <Play size={18} />
                    Generate Code
                  </>
                )}
              </button>
            </div>
          ) : (
            /* File Tree */
            <div className="flex flex-col h-full">
              <div className="px-4 py-3 border-b border-gray-700">
                <div className="flex items-center gap-2 text-gray-400 text-xs font-semibold tracking-wider">
                  <FolderTree size={16} />
                  <span>EXPLORER</span>
                  <span className="ml-auto text-blue-400">{files.length} files</span>
                </div>
              </div>
              <div className="flex-1 overflow-y-auto">
                {tree && tree.children && tree.children.map(child => renderTreeNode(child, 0))}
              </div>
            </div>
          )}
        </div>

        {/* Main Editor Area */}
        <div className="flex-1 flex flex-col bg-gray-900">
          {selectedFile ? (
            <>
              {/* File Tabs */}
              <div className="bg-gray-800 border-b border-gray-700 flex items-center px-2 gap-1 overflow-x-auto">
                {openFiles.map(file => (
                  <div
                    key={file.filepath}
                    className={`flex items-center gap-2 px-3 py-2 cursor-pointer group ${
                      selectedFile.filepath === file.filepath
                        ? 'bg-gray-900 text-white border-t-2 border-blue-500'
                        : 'text-gray-400 hover:text-white hover:bg-gray-700'
                    }`}
                    onClick={() => setSelectedFile(file)}
                  >
                    <span className="text-xs">{getFileIcon(file.filename)}</span>
                    <span className="text-sm font-medium">{file.filename}</span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        closeFile(file);
                      }}
                      className="opacity-0 group-hover:opacity-100 hover:text-red-400 transition"
                    >
                      <X size={14} />
                    </button>
                  </div>
                ))}
              </div>

              {/* Monaco Editor */}
              <div className="flex-1">
                <Editor
                  height="100%"
                  language={getLanguageMode(selectedFile.language)}
                  value={selectedFile.content}
                  theme="vs-dark"
                  options={{
                    readOnly: true,
                    minimap: { enabled: true },
                    fontSize: 14,
                    lineNumbers: 'on',
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                    tabSize: 2,
                  }}
                />
              </div>

              {/* Status Bar */}
              <div className="bg-blue-600 px-4 py-2 flex gap-6 text-xs text-white">
                <span>📝 {selectedFile.content.split('\n').length} lines</span>
                <span>💾 {(selectedFile.content.length / 1024).toFixed(1)} KB</span>
                <span>🔤 {selectedFile.language.toUpperCase()}</span>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <FileCode size={64} className="mx-auto mb-4 opacity-20" />
                <p className="text-lg">No file selected</p>
                <p className="text-sm">Select a file from the explorer to view</p>
              </div>
            </div>
          )}
        </div>

        {/* Activity Panel */}
        <div className="w-96 bg-gray-800/80 border-l border-gray-700 flex flex-col">
          <div className="px-4 py-3 border-b border-gray-700 flex items-center gap-2">
            <Activity size={16} className="text-green-400" />
            <span className="text-sm font-semibold text-white">ACTIVITY LOG</span>
            <span className="ml-auto text-xs text-gray-500">{activityLogs.length} events</span>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {activityLogs.length === 0 ? (
              <div className="text-center text-gray-500 text-sm mt-8">
                No activity yet. Click "Generate Code" to start.
              </div>
            ) : (
              activityLogs.map(log => (
                <div
                  key={log.id}
                  className={`p-3 rounded-lg text-sm ${
                    log.type === 'phase'
                      ? 'bg-blue-500/20 border border-blue-500/30 text-blue-200'
                      : log.type === 'agent'
                      ? 'bg-purple-500/20 border border-purple-500/30 text-purple-200'
                      : log.type === 'file'
                      ? 'bg-green-500/20 border border-green-500/30 text-green-200'
                      : log.type === 'error'
                      ? 'bg-red-500/20 border border-red-500/30 text-red-200'
                      : 'bg-gray-700 border border-gray-600 text-gray-300'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    {log.type === 'phase' && <CheckCircle size={16} className="mt-0.5 flex-shrink-0" />}
                    {log.type === 'agent' && <Loader2 size={16} className="mt-0.5 animate-spin flex-shrink-0" />}
                    {log.type === 'file' && <FileCode size={16} className="mt-0.5 flex-shrink-0" />}
                    {log.type === 'error' && <AlertCircle size={16} className="mt-0.5 flex-shrink-0" />}
                    {log.type === 'success' && <CheckCircle size={16} className="mt-0.5 flex-shrink-0" />}
                    
                    <div className="flex-1 min-w-0">
                      <div className="font-medium break-words">{log.message}</div>
                      <div className="text-xs opacity-70 mt-1">
                        {log.timestamp.toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
            <div ref={activityEndRef} />
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
