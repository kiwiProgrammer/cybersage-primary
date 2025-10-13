import React, { useState } from 'react';
import TaskSubmitForm from './components/TaskSubmitForm';
import TaskFlowVisualization from './components/TaskFlowVisualization';
import AllTasksList from './components/AllTasksList';
import './App.css';

function App() {
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);

  const handleTaskSubmitted = (taskId: string) => {
    setCurrentTaskId(taskId);
  };

  return (
    <div className="App">
      <header className="app-header">
        <h1>CyberSage Task Dashboard</h1>
        <p className="subtitle">Monitor your CTI processing pipeline</p>
      </header>

      <main className="app-main">
        <div className="container">
          <TaskSubmitForm onTaskSubmitted={handleTaskSubmitted} />

          {currentTaskId && <TaskFlowVisualization agentATaskId={currentTaskId} />}

          <AllTasksList />
        </div>
      </main>

      <footer className="app-footer">
        <p>CyberSage Primary - Agent A → Agent B → Agent C Queue</p>
      </footer>
    </div>
  );
}

export default App;
