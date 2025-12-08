// Tej - 78879925

import React, { useState, useEffect } from 'react';
import {
  Activity, DollarSign, Zap, BarChart3,
  TrendingUp, Database, Cpu, RefreshCw,
  ChevronDown, ChevronRight, X, Minimize2
} from 'lucide-react';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface ModelUsage {
  calls: number;
  tokens: number;
  cost: number;
}

interface AgentUsage {
  calls: number;
  tokens: number;
  cost: number;
  models: {
    [key: string]: ModelUsage;
  };
}

interface UsageSummary {
  total_calls: number;
  total_tokens: number;
  total_cost: number;
  average_tokens_per_call: number;
  usage_by_model: {
    [key: string]: ModelUsage;
  };
  usage_by_agent: {
    [key: string]: AgentUsage;
  };
}

interface LLMUsageTrackerProps {
  onClose?: () => void;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

const LLMUsageTracker: React.FC<LLMUsageTrackerProps> = ({
  onClose,
  autoRefresh = true,
  refreshInterval = 3000
}) => {
  const [usageData, setUsageData] = useState<UsageSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedAgents, setExpandedAgents] = useState<Set<string>>(new Set());
  const [expandedModels, setExpandedModels] = useState<Set<string>>(new Set());
  const [isMinimized, setIsMinimized] = useState(false);

  const fetchUsageData = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/usage`);
      if (!response.ok) throw new Error('Failed to fetch usage data');
      const data = await response.json();
      setUsageData(data);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsageData();

    if (autoRefresh) {
      const interval = setInterval(fetchUsageData, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval]);

  const toggleAgent = (agent: string) => {
    setExpandedAgents(prev => {
      const next = new Set(prev);
      if (next.has(agent)) {
        next.delete(agent);
      } else {
        next.add(agent);
      }
      return next;
    });
  };

  const toggleModel = (model: string) => {
    setExpandedModels(prev => {
      const next = new Set(prev);
      if (next.has(model)) {
        next.delete(model);
      } else {
        next.add(model);
      }
      return next;
    });
  };

  const formatNumber = (num: number): string => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(2)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(2)}K`;
    return num.toFixed(0);
  };

  const formatCost = (cost: number): string => {
    return `$${cost.toFixed(4)}`;
  };

  const getAgentIcon = (agent: string): React.ReactNode => {
    const iconMap: { [key: string]: React.ReactNode } = {
      'architect': <Database size={16} className="text-blue-400" />,
      'feature_planner': <BarChart3 size={16} className="text-purple-400" />,
      'code_generator': <Cpu size={16} className="text-green-400" />,
      'batch_code_generator': <Cpu size={16} className="text-emerald-400" />,
      'validator': <Activity size={16} className="text-yellow-400" />,
      'batch_validator': <Activity size={16} className="text-amber-400" />,
      'testing': <Activity size={16} className="text-red-400" />,
    };
    return iconMap[agent] || <Zap size={16} className="text-gray-400" />;
  };

  const getAgentDisplayName = (agent: string): string => {
    const nameMap: { [key: string]: string } = {
      'architect': 'Architect Agent',
      'feature_planner': 'Feature Planner',
      'code_generator': 'Code Generator',
      'batch_code_generator': 'Batch Code Generator',
      'validator': 'Integration Validator',
      'batch_validator': 'Batch Validator',
      'testing': 'Testing Agent',
      'unknown': 'Other',
    };
    return nameMap[agent] || agent.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
  };

  const getModelColor = (model: string): string => {
    if (model.includes('flash')) return 'text-cyan-400';
    if (model.includes('pro')) return 'text-violet-400';
    return 'text-gray-400';
  };

  if (isMinimized) {
    return (
      <div className="fixed bottom-4 right-4 z-50">
        <button
          onClick={() => setIsMinimized(false)}
          className="bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 text-white px-4 py-2 rounded-full shadow-lg flex items-center gap-2 transition-all"
        >
          <Activity size={18} />
          <span className="font-semibold">LLM Usage</span>
          {usageData && (
            <span className="bg-white/20 px-2 py-0.5 rounded-full text-xs">
              {usageData.total_calls} calls
            </span>
          )}
        </button>
      </div>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 w-96 max-h-[600px] bg-gray-800 border border-gray-700 rounded-xl shadow-2xl z-50 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-violet-600 to-purple-600 px-4 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Activity size={20} className="text-white" />
          <h3 className="text-white font-bold text-sm">LLM Usage Tracking</h3>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchUsageData}
            className="p-1 hover:bg-white/20 rounded transition-colors"
            title="Refresh"
          >
            <RefreshCw size={16} className="text-white" />
          </button>
          <button
            onClick={() => setIsMinimized(true)}
            className="p-1 hover:bg-white/20 rounded transition-colors"
            title="Minimize"
          >
            <Minimize2 size={16} className="text-white" />
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1 hover:bg-white/20 rounded transition-colors"
              title="Close"
            >
              <X size={16} className="text-white" />
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar scrollbar-w-2 scrollbar-thumb-violet-500/50 scrollbar-track-transparent">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="animate-spin text-violet-400" size={24} />
          </div>
        ) : error ? (
          <div className="text-center py-8">
            <p className="text-red-400 text-sm">{error}</p>
            <button
              onClick={fetchUsageData}
              className="mt-2 text-xs text-gray-400 hover:text-white"
            >
              Retry
            </button>
          </div>
        ) : usageData ? (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-gradient-to-br from-blue-600/20 to-blue-600/5 border border-blue-500/30 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1">
                  <Activity size={14} className="text-blue-400" />
                  <span className="text-xs text-gray-400">Total Calls</span>
                </div>
                <div className="text-xl font-bold text-white">
                  {usageData.total_calls}
                </div>
              </div>

              <div className="bg-gradient-to-br from-emerald-600/20 to-emerald-600/5 border border-emerald-500/30 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1">
                  <Zap size={14} className="text-emerald-400" />
                  <span className="text-xs text-gray-400">Total Tokens</span>
                </div>
                <div className="text-xl font-bold text-white">
                  {formatNumber(usageData.total_tokens)}
                </div>
              </div>

              <div className="bg-gradient-to-br from-purple-600/20 to-purple-600/5 border border-purple-500/30 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1">
                  <DollarSign size={14} className="text-purple-400" />
                  <span className="text-xs text-gray-400">Total Cost</span>
                </div>
                <div className="text-xl font-bold text-white">
                  {formatCost(usageData.total_cost)}
                </div>
              </div>

              <div className="bg-gradient-to-br from-cyan-600/20 to-cyan-600/5 border border-cyan-500/30 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1">
                  <TrendingUp size={14} className="text-cyan-400" />
                  <span className="text-xs text-gray-400">Avg/Call</span>
                </div>
                <div className="text-xl font-bold text-white">
                  {formatNumber(usageData.average_tokens_per_call)}
                </div>
              </div>
            </div>

            {/* Usage by Agent */}
            {Object.keys(usageData.usage_by_agent).length > 0 && (
              <div className="bg-gray-900/50 border border-gray-700 rounded-lg overflow-hidden">
                <div className="bg-gray-800 px-3 py-2 border-b border-gray-700">
                  <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                    <BarChart3 size={14} className="text-violet-400" />
                    Usage by Agent
                  </h4>
                </div>
                <div className="divide-y divide-gray-700">
                  {Object.entries(usageData.usage_by_agent)
                    .sort((a, b) => b[1].calls - a[1].calls)
                    .map(([agent, stats]) => {
                      const isExpanded = expandedAgents.has(agent);
                      const percentage = ((stats.calls / usageData.total_calls) * 100).toFixed(1);
                      
                      return (
                        <div key={agent} className="bg-gray-900/30">
                          <div
                            className="px-3 py-2 hover:bg-gray-800/50 cursor-pointer transition-colors"
                            onClick={() => toggleAgent(agent)}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2 flex-1">
                                {isExpanded ? (
                                  <ChevronDown size={14} className="text-gray-400 shrink-0" />
                                ) : (
                                  <ChevronRight size={14} className="text-gray-400 shrink-0" />
                                )}
                                {getAgentIcon(agent)}
                                <span className="text-xs font-medium text-gray-200 truncate">
                                  {getAgentDisplayName(agent)}
                                </span>
                              </div>
                              <div className="flex items-center gap-3 shrink-0">
                                <span className="text-xs text-gray-400">
                                  {stats.calls} calls
                                </span>
                                <span className="text-xs text-gray-500">
                                  {percentage}%
                                </span>
                              </div>
                            </div>
                            
                            {/* Progress bar */}
                            <div className="mt-2 h-1 bg-gray-700 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-gradient-to-r from-violet-500 to-purple-500 transition-all"
                                style={{ width: `${percentage}%` }}
                              />
                            </div>
                          </div>
                          
                          {isExpanded && (
                            <div className="px-3 py-2 bg-gray-900/50 space-y-2">
                              <div className="grid grid-cols-3 gap-2 text-xs">
                                <div>
                                  <div className="text-gray-500">Tokens</div>
                                  <div className="text-gray-200 font-medium">
                                    {formatNumber(stats.tokens)}
                                  </div>
                                </div>
                                <div>
                                  <div className="text-gray-500">Cost</div>
                                  <div className="text-gray-200 font-medium">
                                    {formatCost(stats.cost)}
                                  </div>
                                </div>
                                <div>
                                  <div className="text-gray-500">Avg Tokens</div>
                                  <div className="text-gray-200 font-medium">
                                    {formatNumber(stats.tokens / stats.calls)}
                                  </div>
                                </div>
                              </div>
                              
                              {/* Models used by this agent */}
                              {Object.keys(stats.models).length > 0 && (
                                <div className="mt-2 pt-2 border-t border-gray-700/50">
                                  <div className="text-xs text-gray-500 mb-1">Models:</div>
                                  <div className="space-y-1">
                                    {Object.entries(stats.models).map(([model, modelStats]) => (
                                      <div key={model} className="flex items-center justify-between text-xs">
                                        <span className={`font-mono ${getModelColor(model)}`}>
                                          {model}
                                        </span>
                                        <span className="text-gray-400">
                                          {modelStats.calls} calls
                                        </span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                </div>
              </div>
            )}

            {/* Usage by Model */}
            {Object.keys(usageData.usage_by_model).length > 0 && (
              <div className="bg-gray-900/50 border border-gray-700 rounded-lg overflow-hidden">
                <div className="bg-gray-800 px-3 py-2 border-b border-gray-700">
                  <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Cpu size={14} className="text-cyan-400" />
                    Usage by Model
                  </h4>
                </div>
                <div className="divide-y divide-gray-700">
                  {Object.entries(usageData.usage_by_model)
                    .sort((a, b) => b[1].calls - a[1].calls)
                    .map(([model, stats]) => {
                      const isExpanded = expandedModels.has(model);
                      const percentage = ((stats.calls / usageData.total_calls) * 100).toFixed(1);
                      
                      return (
                        <div key={model} className="bg-gray-900/30">
                          <div
                            className="px-3 py-2 hover:bg-gray-800/50 cursor-pointer transition-colors"
                            onClick={() => toggleModel(model)}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                {isExpanded ? (
                                  <ChevronDown size={14} className="text-gray-400" />
                                ) : (
                                  <ChevronRight size={14} className="text-gray-400" />
                                )}
                                <span className={`text-xs font-mono font-medium ${getModelColor(model)}`}>
                                  {model}
                                </span>
                              </div>
                              <span className="text-xs text-gray-400">
                                {stats.calls} calls ({percentage}%)
                              </span>
                            </div>
                          </div>
                          
                          {isExpanded && (
                            <div className="px-3 py-2 bg-gray-900/50">
                              <div className="grid grid-cols-3 gap-2 text-xs">
                                <div>
                                  <div className="text-gray-500">Tokens</div>
                                  <div className="text-gray-200 font-medium">
                                    {formatNumber(stats.tokens)}
                                  </div>
                                </div>
                                <div>
                                  <div className="text-gray-500">Cost</div>
                                  <div className="text-gray-200 font-medium">
                                    {formatCost(stats.cost)}
                                  </div>
                                </div>
                                <div>
                                  <div className="text-gray-500">Avg Tokens</div>
                                  <div className="text-gray-200 font-medium">
                                    {formatNumber(stats.tokens / stats.calls)}
                                  </div>
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-8 text-gray-400 text-sm">
            No usage data available
          </div>
        )}
      </div>

      {/* Footer */}
      {usageData && (
        <div className="bg-gray-900 border-t border-gray-700 px-4 py-2 shrink-0">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>Auto-refreshing every {refreshInterval / 1000}s</span>
            <span className="text-gray-600">Live tracking</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default LLMUsageTracker;

