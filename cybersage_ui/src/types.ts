// Agent A Types
export interface AgentARunRequest {
  urls: string[];
  output_dir?: string;
  auth_username?: string;
  auth_password?: string;
  no_ssl_verify?: boolean;
  bypass_memory?: boolean;
  log_level?: string;
}

export interface AgentATaskResponse {
  task_id: string;
  status: string;
  submitted_at: string;
  started_at?: string;
  completed_at?: string;
  result?: {
    success: boolean;
    exit_code: number;
    output: string;
    error?: string;
  };
}

// Agent B Types
export interface AgentBTaskInfo {
  task_id: string;
  status: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  message_data?: any;
  file_count?: number;
  merged_file?: string;
  error?: string;
}

export interface AgentBTaskListResponse {
  total: number;
  tasks: AgentBTaskInfo[];
}

// Agent C Queue Types
export interface AgentCQueueTaskInfo {
  task_id: string;
  status: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  message_data?: any;
  file_count?: number;
  processed_files?: string[];
  agent_c_task_id?: string;
  error?: string;
}

export interface AgentCQueueTaskListResponse {
  total: number;
  tasks: AgentCQueueTaskInfo[];
}

// Combined Task Flow
export interface TaskFlow {
  agentATaskId: string;
  agentAStatus: string;
  agentBTasks: AgentBTaskInfo[];
  agentCTasks: AgentCQueueTaskInfo[];
  createdAt: string;
}
