#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Agent Coordinator for task distribution and management
"""

from typing import List, Dict, Any, Optional
from queue import PriorityQueue
import threading
from .base import BaseAgent, AgentTask, AgentResult, TaskStatus

class AgentCoordinator:
    """Coordinates multiple agents and distributes tasks"""
    
    def __init__(self, config: Any):
        self.config = config
        self.agents: Dict[str, BaseAgent] = {}
        self.task_queue = PriorityQueue()
        self.active_tasks: Dict[str, AgentTask] = {}
        self.completed_tasks: Dict[str, AgentResult] = {}
        self.failed_tasks: Dict[str, AgentResult] = {}
        self._lock = threading.Lock()
    
    def register_agent(self, agent: BaseAgent):
        """Register an agent with the coordinator"""
        with self._lock:
            self.agents[agent.agent_id] = agent
            print(f"✅ Registered agent: {agent.agent_id} with capabilities: {[c.value for c in agent.capabilities]}")
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent"""
        with self._lock:
            if agent_id in self.agents:
                del self.agents[agent_id]
                print(f"❌ Unregistered agent: {agent_id}")
    
    def submit_task(self, task: AgentTask) -> str:
        """Submit a task for execution"""
        with self._lock:
            # Add to queue with priority (negative for max heap behavior)
            self.task_queue.put((-task.priority, task.task_id, task))
            print(f"📋 Task submitted: {task.task_id} (type: {task.task_type}, priority: {task.priority})")
            return task.task_id
    
    def find_capable_agent(self, task: AgentTask) -> Optional[BaseAgent]:
        """Find an agent capable of handling the task"""
        with self._lock:
            # Sort agents by success rate
            sorted_agents = sorted(
                [a for a in self.agents.values() if a.active],
                key=lambda x: (x.success_count / max(x.task_count, 1)),
                reverse=True
            )
            
            for agent in sorted_agents:
                if agent.can_handle(task):
                    return agent
            
            return None
    
    def execute_task(self, task: AgentTask) -> Optional[AgentResult]:
        """Execute a single task"""
        # Find capable agent
        agent = self.find_capable_agent(task)
        
        if not agent:
            print(f"❌ No capable agent found for task: {task.task_id}")
            result = AgentResult(
                task_id=task.task_id,
                agent_id="none",
                success=False,
                error_message="No capable agent available"
            )
            with self._lock:
                self.failed_tasks[task.task_id] = result
            return result
        
        # Execute task
        print(f"🔄 Executing task {task.task_id} with agent {agent.agent_id}")
        
        with self._lock:
            self.active_tasks[task.task_id] = task
        
        result = agent.execute(task)
        
        with self._lock:
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]
            
            if result.success:
                self.completed_tasks[task.task_id] = result
                print(f"✅ Task {task.task_id} completed successfully in {result.execution_time:.2f}s")
            else:
                self.failed_tasks[task.task_id] = result
                print(f"❌ Task {task.task_id} failed: {result.error_message}")
        
        return result
    
    def execute_next_task(self) -> Optional[AgentResult]:
        """Execute the next task in queue"""
        if self.task_queue.empty():
            return None
        
        _, task_id, task = self.task_queue.get()
        return self.execute_task(task)
    
    def execute_all_tasks(self) -> List[AgentResult]:
        """Execute all tasks in queue"""
        results = []
        
        while not self.task_queue.empty():
            result = self.execute_next_task()
            if result:
                results.append(result)
        
        return results
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        with self._lock:
            if task_id in self.completed_tasks:
                return {
                    "status": "completed",
                    "result": self.completed_tasks[task_id].to_dict()
                }
            elif task_id in self.failed_tasks:
                return {
                    "status": "failed",
                    "result": self.failed_tasks[task_id].to_dict()
                }
            elif task_id in self.active_tasks:
                return {
                    "status": "active",
                    "task": {
                        "task_id": task_id,
                        "task_type": self.active_tasks[task_id].task_type,
                        "status": self.active_tasks[task_id].status.value
                    }
                }
            else:
                return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get coordinator statistics"""
        with self._lock:
            return {
                "registered_agents": len(self.agents),
                "active_agents": sum(1 for a in self.agents.values() if a.active),
                "queued_tasks": self.task_queue.qsize(),
                "active_tasks": len(self.active_tasks),
                "completed_tasks": len(self.completed_tasks),
                "failed_tasks": len(self.failed_tasks),
                "agent_stats": {
                    agent_id: agent.get_stats()
                    for agent_id, agent in self.agents.items()
                }
            }
    
    def clear_history(self):
        """Clear completed and failed task history"""
        with self._lock:
            self.completed_tasks.clear()
            self.failed_tasks.clear()
            print("🧹 Task history cleared")
