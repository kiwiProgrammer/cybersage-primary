import React, { useEffect, useState } from 'react';
import { agentAApi, agentBApi, agentCQueueApi } from '../api';
import { AgentATaskResponse, AgentBTaskInfo, AgentCQueueTaskInfo } from '../types';
import './TaskFlowVisualization.css';

interface TaskFlowVisualizationProps {
  agentATaskId: string;
}

const TaskFlowVisualization: React.FC<TaskFlowVisualizationProps> = ({ agentATaskId }) => {
  const [agentATask, setAgentATask] = useState<AgentATaskResponse | null>(null);
  const [agentBTasks, setAgentBTasks] = useState<AgentBTaskInfo[]>([]);
  const [agentCTasks, setAgentCTasks] = useState<AgentCQueueTaskInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch Agent A task
        const agentAData = await agentAApi.getTaskStatus(agentATaskId);
        setAgentATask(agentAData);

        // Fetch Agent B tasks (all recent tasks)
        const agentBData = await agentBApi.listTasks(undefined, 20);
        setAgentBTasks(agentBData.tasks);

        // Fetch Agent C tasks (all recent tasks)
        const agentCData = await agentCQueueApi.listTasks(undefined, 20);
        setAgentCTasks(agentCData.tasks);
      } catch (error) {
        console.error('Error fetching task data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000); // Poll every 5 seconds

    return () => clearInterval(interval);
  }, [agentATaskId]);

  if (loading) {
    return <div className="loading">Loading task flow...</div>;
  }

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

  return (
    <div className="task-flow-visualization">
      <h2>Task Flow: {agentATaskId}</h2>

      <div className="flow-container">
        {/* Agent A */}
        <div className="flow-stage">
          <div className="stage-header">
            <h3>Agent A</h3>
            <span className="stage-subtitle">CTI URL Processing</span>
          </div>
          {agentATask && (
            <div className="task-card" style={{ borderLeft: `4px solid ${getStatusColor(agentATask.status)}` }}>
              <div className="task-status">
                <span className="status-badge" style={{ backgroundColor: getStatusColor(agentATask.status) }}>
                  {agentATask.status}
                </span>
              </div>
              <div className="task-details">
                <p><strong>Task ID:</strong> {agentATask.task_id.substring(0, 8)}...</p>
                <p><strong>Submitted:</strong> {new Date(agentATask.submitted_at).toLocaleString()}</p>
                {agentATask.started_at && (
                  <p><strong>Started:</strong> {new Date(agentATask.started_at).toLocaleString()}</p>
                )}
                {agentATask.completed_at && (
                  <p><strong>Completed:</strong> {new Date(agentATask.completed_at).toLocaleString()}</p>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="flow-arrow">→</div>

        {/* Agent B */}
        <div className="flow-stage">
          <div className="stage-header">
            <h3>Agent B</h3>
            <span className="stage-subtitle">Transform & Ingest</span>
          </div>
          {agentBTasks.length > 0 ? (
            agentBTasks.slice(0, 3).map((task) => (
              <div key={task.task_id} className="task-card" style={{ borderLeft: `4px solid ${getStatusColor(task.status)}` }}>
                <div className="task-status">
                  <span className="status-badge" style={{ backgroundColor: getStatusColor(task.status) }}>
                    {task.status}
                  </span>
                </div>
                <div className="task-details">
                  <p><strong>Task ID:</strong> {task.task_id.substring(0, 8)}...</p>
                  <p><strong>Created:</strong> {new Date(task.created_at).toLocaleString()}</p>
                  {task.file_count !== null && task.file_count !== undefined && (
                    <p><strong>Files:</strong> {task.file_count}</p>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="no-tasks">Waiting for tasks...</div>
          )}
        </div>

        <div className="flow-arrow">→</div>

        {/* Agent C */}
        <div className="flow-stage">
          <div className="stage-header">
            <h3>Agent C Queue</h3>
            <span className="stage-subtitle">Vulnerability Analysis</span>
          </div>
          {agentCTasks.length > 0 ? (
            agentCTasks.slice(0, 3).map((task) => (
              <div key={task.task_id} className="task-card" style={{ borderLeft: `4px solid ${getStatusColor(task.status)}` }}>
                <div className="task-status">
                  <span className="status-badge" style={{ backgroundColor: getStatusColor(task.status) }}>
                    {task.status}
                  </span>
                </div>
                <div className="task-details">
                  <p><strong>Task ID:</strong> {task.task_id.substring(0, 8)}...</p>
                  <p><strong>Created:</strong> {new Date(task.created_at).toLocaleString()}</p>
                  {task.processed_files && (
                    <p><strong>Processed:</strong> {task.processed_files.length} files</p>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="no-tasks">Waiting for tasks...</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TaskFlowVisualization;
