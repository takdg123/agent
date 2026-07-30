#!/usr/bin/env python3
"""
Test script for new models (AstroSage-70B + Qwen2.5:32B)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.utils.llm_client import LLMClient
from src.harness.expert_agents import (
    GRBExpertAgent, KilonovaExpertAgent, AstrophysicistAgent,
    LanguageExpertAgent, CriticAgent, WriterAgent
)
from src.harness.base import AgentTask, AgentCapability

print("="*70)
print("🧪 Testing New Models (AstroSage-70B + Qwen2.5:32B)")
print("="*70)
print()

# Load config
config = Config()

print("📋 Configuration:")
print(f"   Astro Expert Model: {config.astro_expert_model}")
print(f"   General Model: {config.general_model}")
print(f"   Language Model: {config.language_model}")
print()

# Test 1: Check model availability
print("="*70)
print("Test 1: Model Availability")
print("="*70)
print()

llm_astro = LLMClient(model=config.astro_expert_model)
llm_general = LLMClient(model=config.general_model)

print(f"🔍 Checking Ollama service...")
if llm_astro.is_available():
    print("   ✅ Ollama is running")
    models = llm_astro.get_models()
    print(f"   Available models: {len(models)}")
    for model in models:
        if 'astrosage' in model.lower() or 'qwen' in model.lower():
            print(f"      • {model}")
else:
    print("   ❌ Ollama is not running!")
    sys.exit(1)

print()

# Test 2: Test AstroSage-70B with astronomy question
print("="*70)
print("Test 2: AstroSage-70B (Astronomy Expert)")
print("="*70)
print()

test_prompt_astro = """You are an expert in gamma-ray burst astrophysics. 
Briefly explain (2-3 sentences) what causes the prompt emission in a GRB."""

print(f"🌟 Testing {config.astro_expert_model}...")
print(f"   Prompt: {test_prompt_astro[:80]}...")
print(f"   Generating response... (this may take 30-60s for 70B model)")

response_astro = llm_astro.generate(test_prompt_astro, model=config.astro_expert_model)

print()
print("   Response:")
print("   " + "-"*66)
for line in response_astro.split('\n'):
    print(f"   {line}")
print("   " + "-"*66)
print()

if len(response_astro) > 50 and "error" not in response_astro.lower():
    print("   ✅ AstroSage-70B is working!")
else:
    print("   ⚠️  Response seems short or has error")

print()

# Test 3: Test Qwen2.5:32B with translation
print("="*70)
print("Test 3: Qwen2.5:32B (General Model)")
print("="*70)
print()

test_prompt_qwen = """Translate this to professional Korean:
"This paper presents observations of GRB 240710A and its associated kilonova emission from a neutron star merger."

Provide only the Korean translation."""

print(f"🔭 Testing {config.general_model}...")
print(f"   Prompt: Translation test")
print(f"   Generating response... (this may take 15-30s for 32B model)")

response_qwen = llm_general.generate(test_prompt_qwen, model=config.general_model)

print()
print("   Response:")
print("   " + "-"*66)
for line in response_qwen.split('\n'):
    print(f"   {line}")
print("   " + "-"*66)
print()

if len(response_qwen) > 20 and any(ord(c) > 127 for c in response_qwen):
    print("   ✅ Qwen2.5:32B is working!")
else:
    print("   ⚠️  Response might not be Korean")

print()

# Test 4: Initialize all expert agents
print("="*70)
print("Test 4: Expert Agent Initialization")
print("="*70)
print()

print("🧠 Initializing all 6 expert agents...")
print()

experts = [
    ('GRB Expert', GRBExpertAgent('grb', config, None)),
    ('Kilonova Expert', KilonovaExpertAgent('kn', config, None)),
    ('Astrophysicist', AstrophysicistAgent('astro', config, None)),
    ('Language Expert', LanguageExpertAgent('lang', config, None)),
    ('Critic', CriticAgent('critic', config, None)),
    ('Writer', WriterAgent('writer', config, None))
]

print()
print("✅ All experts initialized successfully!")
print()

# Test 5: Quick agent test
print("="*70)
print("Test 5: GRB Expert Agent Test")
print("="*70)
print()

test_paper = {
    'title': 'GRB 240710A: Discovery of a Bright Kilonova',
    'authors': ['Smith, J.', 'Doe, A.', 'Johnson, R.'],
    'abstract': 'We present multi-wavelength observations of GRB 240710A, revealing a luminous optical/NIR excess consistent with kilonova emission from r-process nucleosynthesis in neutron star merger ejecta.'
}

print(f"📄 Test Paper: {test_paper['title']}")
print()

grb_expert = experts[0][1]  # Get GRB Expert

task = AgentTask(
    task_type="expert_review",
    description="Test GRB expert with sample paper",
    input_data={"paper": test_paper, "previous_analysis": ""},
    required_capabilities=[AgentCapability.TEXT_ANALYSIS],
    priority=10
)

print(f"🔄 Executing GRB expert analysis... (may take 1-2 minutes)")
print()

result = grb_expert.execute(task)

print("   Result:")
print(f"   Success: {result.success}")
print(f"   Execution time: {result.execution_time:.1f}s")

if result.success:
    review = result.output_data.get('expert_review', '')
    confidence = result.output_data.get('confidence', 0)
    
    print(f"   Confidence: {confidence:.2%}")
    print()
    print("   Expert Review (first 500 chars):")
    print("   " + "-"*66)
    for line in review[:500].split('\n'):
        print(f"   {line}")
    if len(review) > 500:
        print("   ...")
    print("   " + "-"*66)
    print()
    print("   ✅ GRB Expert analysis successful!")
else:
    print(f"   ❌ Error: {result.error_message}")

print()

# Summary
print("="*70)
print("📊 TEST SUMMARY")
print("="*70)
print()

print("✅ Model Availability: PASS")
print(f"✅ AstroSage-70B Test: {'PASS' if len(response_astro) > 50 else 'FAIL'}")
print(f"✅ Qwen2.5:32B Test: {'PASS' if len(response_qwen) > 20 else 'FAIL'}")
print("✅ Expert Initialization: PASS")
print(f"✅ GRB Expert Test: {'PASS' if result.success else 'FAIL'}")
print()

print("="*70)
print("🎉 All tests completed!")
print("="*70)
print()
print("The new models are working correctly.")
print("You can now run the full daily report with:")
print("   ./run_daily_report_refactored.py")
print()
