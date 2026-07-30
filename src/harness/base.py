#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Base classes for Agent Harness System
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum
import time
import uuid

class AgentCapability(Enum):
    """Capabilities that an agent can have"""
    TEXT_ANALYSIS = "text_analysis"
    VISION_ANALYSIS = "vision_analysis"
    SUMMARIZATION = "summarization"
    QUESTION_ANSWERING = "question_answering"
    INFORMATION_EXTRACTION = "information_extraction"
    COMPARISON = "comparison"
    SYNTHESIS = "synthesis"

class TaskStatus(Enum):
    """Status of a task"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class AgentTask:
    """Represents a task for an agent to execute"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str = ""
    description: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    required_capabilities: List[AgentCapability] = field(default_factory=list)
    priority: int = 1  # 1-10, higher is more important
    parent_task_id: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    def start(self):
        """Mark task as started"""
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = time.time()
    
    def complete(self):
        """Mark task as completed"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = time.time()
    
    def fail(self):
        """Mark task as failed"""
        self.status = TaskStatus.FAILED
        self.completed_at = time.time()
    
    def get_duration(self) -> Optional[float]:
        """Get task duration in seconds"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None

@dataclass
class AgentResult:
    """Result from an agent execution"""
    task_id: str
    agent_id: str
    success: bool
    output_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "success": self.success,
            "output_data": self.output_data,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "metadata": self.metadata
        }

class BaseAgent(ABC):
    """Abstract base class for all agents in the harness"""
    
    def __init__(self, agent_id: str, config: Any):
        self.agent_id = agent_id
        self.config = config
        self.capabilities: List[AgentCapability] = []
        self.active = True
        self.task_count = 0
        self.success_count = 0
        self.failure_count = 0
    
    @abstractmethod
    def can_handle(self, task: AgentTask) -> bool:
        """Check if this agent can handle the given task"""
        pass
    
    @abstractmethod
    def execute(self, task: AgentTask) -> AgentResult:
        """Execute the given task"""
        pass
    
    def get_capabilities(self) -> List[AgentCapability]:
        """Get agent capabilities"""
        return self.capabilities
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        return {
            "agent_id": self.agent_id,
            "active": self.active,
            "capabilities": [c.value for c in self.capabilities],
            "task_count": self.task_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_count / self.task_count if self.task_count > 0 else 0
        }
    
    def _record_task_result(self, success: bool):
        """Record task execution result"""
        self.task_count += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
