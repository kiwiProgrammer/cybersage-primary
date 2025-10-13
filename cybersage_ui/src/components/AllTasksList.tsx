import React, { useEffect, useState } from 'react';
import { agentBApi, agentCQueueApi } from '../api';
import { AgentBTaskInfo, AgentCQueueTaskInfo } from '../types';
import './AllTasksList.css';

const AllTasksList: React.FC = () => {
  const [agentBTasks, setAgentBTasks] = useState<AgentBTaskInfo[]>([]);
  const [agentCTasks, setAgentCTasks] = useState<AgentCQueueTaskInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'agent_b' | 'agent_c'>('agent_b');

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        const [agentBData, agentCData] = await Promise.all([
          agentBApi.listTasks(undefined, 50),
          agentCQueueApi.listTasks(undefined, 50),
        ]);

        setAgentBTasks(agentBData.tasks);
        setAgentCTasks(agentCData.tasks);
      } catch (error) {
        console.error('Error fetching tasks:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchTasks();
    const interval = setInterval(fetchTasks, 10000); // Poll every 10 seconds

    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return '#4caf50';
      case 'running':
      case 'processing':
      case 'in_progress':
        return '#2196f3';
      case 'pending':
      case 'queued':
        return '#ff9800';
      case 'failed':
        return '#f44336';
      default:
        return '#9e9e9e';
    }
  };

  if (loading) {
    return <div className="loading">Loading tasks...</div>;
  }

  return (
    <div className="all-tasks-list">
      <h2>All Tasks</h2>

      <div className="tabs">
        <button
          className={activeTab === 'agent_b' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('agent_b')}
        >
          Agent B ({agentBTasks.length})
        </button>
        <button
          className={activeTab === 'agent_c' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('agent_c')}
        >
          Agent C Queue ({agentCTasks.length})
        </button>
      </div>

      <div className="tasks-container">
        {activeTab === 'agent_b' && (
          <>
            {agentBTasks.length === 0 ? (
              <div className="no-tasks">No tasks found</div>
            ) : (
              <div className="tasks-grid">
                {agentBTasks.map((task) => (
                  <div key={task.task_id} className="task-item">
                    <div className="task-header">
                      <span
                        className="status-indicator"
                        style={{ backgroundColor: getStatusColor(task.status) }}
                      ></span>
                      <span className="task-id">{task.task_id.substring(0, 12)}...</span>
                    </div>
                    <div className="task-info">
                      <p>
                        <strong>Status:</strong>{' '}
                        <span style={{ color: getStatusColor(task.status) }}>{task.status}</span>
                      </p>
                      <p>
                        <strong>Created:</strong> {new Date(task.created_at).toLocaleString()}
                      </p>
                      {task.file_count !== null && task.file_count !== undefined && (
                        <p>
                          <strong>Files:</strong> {task.file_count}
                        </p>
                      )}
                      {task.error && (
                        <p className="error-text">
                          <strong>Error:</strong> {task.error}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {activeTab === 'agent_c' && (
          <>
            {agentCTasks.length === 0 ? (
              <div className="no-tasks">No tasks found</div>
            ) : (
              <div className="tasks-grid">
                {agentCTasks.map((task) => (
                  <div key={task.task_id} className="task-item">
                    <div className="task-header">
                      <span
                        className="status-indicator"
                        style={{ backgroundColor: getStatusColor(task.status) }}
                      ></span>
                      <span className="task-id">{task.task_id.substring(0, 12)}...</span>
                    </div>
                    <div className="task-info">
                      <p>
                        <strong>Status:</strong>{' '}
                        <span style={{ color: getStatusColor(task.status) }}>{task.status}</span>
                      </p>
                      <p>
                        <strong>Created:</strong> {new Date(task.created_at).toLocaleString()}
                      </p>
                      {task.processed_files && (
                        <p>
                          <strong>Processed:</strong> {task.processed_files.length} files
                        </p>
                      )}
                      {task.agent_c_task_id && (
                        <p>
                          <strong>Agent C Task:</strong> {task.agent_c_task_id.substring(0, 12)}...
                        </p>
                      )}
                      {task.error && (
                        <p className="error-text">
                          <strong>Error:</strong> {task.error}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default AllTasksList;
