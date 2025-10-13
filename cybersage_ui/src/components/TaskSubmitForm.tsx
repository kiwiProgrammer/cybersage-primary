import React, { useState } from 'react';
import { agentAApi } from '../api';
import { AgentARunRequest } from '../types';
import './TaskSubmitForm.css';

interface TaskSubmitFormProps {
  onTaskSubmitted: (taskId: string) => void;
}

const TaskSubmitForm: React.FC<TaskSubmitFormProps> = ({ onTaskSubmitted }) => {
  const [urls, setUrls] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);

    try {
      const urlList = urls
        .split('\n')
        .map((url) => url.trim())
        .filter((url) => url.length > 0);

      if (urlList.length === 0) {
        throw new Error('Please enter at least one URL');
      }

      const request: AgentARunRequest = {
        urls: urlList,
        log_level: 'INFO',
      };

      const response = await agentAApi.submitTask(request);
      setSuccess(`Task submitted successfully! Task ID: ${response.task_id}`);
      onTaskSubmitted(response.task_id);
      setUrls('');
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to submit task');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="task-submit-form">
      <h2>Submit CTI URLs for Processing</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="urls">URLs (one per line):</label>
          <textarea
            id="urls"
            value={urls}
            onChange={(e) => setUrls(e.target.value)}
            placeholder="https://example.com/cti-report-1&#10;https://example.com/cti-report-2"
            rows={5}
            disabled={loading}
          />
        </div>

        <button type="submit" disabled={loading}>
          {loading ? 'Submitting...' : 'Submit Task'}
        </button>

        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}
      </form>
    </div>
  );
};

export default TaskSubmitForm;
