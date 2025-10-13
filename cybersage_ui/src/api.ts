import axios from 'axios';
import {
  AgentARunRequest,
  AgentATaskResponse,
  AgentBTaskListResponse,
  AgentBTaskInfo,
  AgentCQueueTaskListResponse,
  AgentCQueueTaskInfo,
} from './types';

// API Base URLs
const AGENT_A_URL = process.env.REACT_APP_AGENT_A_URL || 'http://localhost:8090';
const AGENT_B_URL = process.env.REACT_APP_AGENT_B_URL || 'http://localhost:8200';
const AGENT_C_QUEUE_URL = process.env.REACT_APP_AGENT_C_QUEUE_URL || 'http://localhost:8300';

// Agent A API
export const agentAApi = {
  submitTask: async (request: AgentARunRequest): Promise<{ task_id: string; status: string; message: string }> => {
    const response = await axios.post(`${AGENT_A_URL}/run`, request);
    return response.data;
  },

  getTaskStatus: async (taskId: string): Promise<AgentATaskResponse> => {
    const response = await axios.get(`${AGENT_A_URL}/task/${taskId}`);
    return response.data;
  },

  healthCheck: async () => {
    const response = await axios.get(`${AGENT_A_URL}/health`);
    return response.data;
  },
};

// Agent B API
export const agentBApi = {
  listTasks: async (status?: string, limit: number = 100): Promise<AgentBTaskListResponse> => {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    params.append('limit', limit.toString());

    const response = await axios.get(`${AGENT_B_URL}/tasks?${params.toString()}`);
    return response.data;
  },

  getTaskStatus: async (taskId: string): Promise<{ task: AgentBTaskInfo }> => {
    const response = await axios.get(`${AGENT_B_URL}/tasks/${taskId}`);
    return response.data;
  },

  healthCheck: async () => {
    const response = await axios.get(`${AGENT_B_URL}/health`);
    return response.data;
  },
};

// Agent C Queue API
export const agentCQueueApi = {
  listTasks: async (status?: string, limit: number = 100): Promise<AgentCQueueTaskListResponse> => {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    params.append('limit', limit.toString());

    const response = await axios.get(`${AGENT_C_QUEUE_URL}/tasks?${params.toString()}`);
    return response.data;
  },

  getTaskStatus: async (taskId: string): Promise<{ task: AgentCQueueTaskInfo }> => {
    const response = await axios.get(`${AGENT_C_QUEUE_URL}/tasks/${taskId}`);
    return response.data;
  },

  healthCheck: async () => {
    const response = await axios.get(`${AGENT_C_QUEUE_URL}/health`);
    return response.data;
  },
};
