# Prompt Refactoring Summary

## Overview
Refactored all hardcoded prompts in `torri/src` to external `.txt` files in `torri/prompts/` for easy editing and maintenance.

## Changes Made

### 1. Removed Old Unused Prompts
Deleted 6 old `.txt` files that were only used in archived code:
- `comparison.txt`
- `daily_report.txt`
- `paper_analysis_optimized.txt`
- `paper_summary.txt`
- `quick_summary.txt`
- `vision_analysis.txt`

### 2. Created New Prompt Files
Created 9 new prompt files for active code in `torri/prompts/`:

| File | Purpose | Used By | Model |
|------|---------|---------|-------|
| `grb_expert.txt` | GRB expert analysis | `GRBExpertAgent` | astrosage:70b-q4_K_M |
| `kilonova_expert.txt` | Kilonova expert analysis | `KilonovaExpertAgent` | astrosage:70b-q4_K_M |
| `astrophysicist_synthesis.txt` | Broader scientific context | `AstrophysicistAgent` | qwen2.5:32b |
| `language_expert.txt` | English-Korean translation | `LanguageExpertAgent` | qwen2.5:32b |
| `critic.txt` | Quality review and critique | `CriticAgent` | qwen2.5:32b |
| `writer.txt` | Professional science writing | `WriterAgent` | qwen2.5:32b |
| `report_fixer_en.txt` | Report regeneration (English) | `ReportFixer` | qwen2.5:7b |
| `report_fixer_ko.txt` | Report regeneration (Korean) | `ReportFixer` | qwen2.5:7b |
| `report_validator.txt` | Report quality validation | `ReportValidator` | qwen2.5:7b |

### 3. Updated Code Files

#### `src/utils/prompt_loader.py`
- Replaced old methods with new ones for the 9 active prompts
- Each method loads and formats the corresponding `.txt` file

#### `src/harness/expert_agents.py`
- Added `PromptLoader` import and initialization in `BaseExpertAgent`
- Updated 6 agent classes to use `prompt_loader` instead of hardcoded strings:
  - `GRBExpertAgent`
  - `KilonovaExpertAgent`
  - `AstrophysicistAgent`
  - `LanguageExpertAgent`
  - `CriticAgent`
  - `WriterAgent`

#### `src/report_fixer.py`
- Added `PromptLoader` initialization
- Updated `regenerate_paper_analysis()` to use prompt loader for both English and Korean prompts

#### `src/report_validator.py`
- Added `PromptLoader` initialization
- Updated `_llm_based_review()` to use prompt loader

#### `config/prompts.yml`
- Updated configuration to document all 9 new prompts
- Added model assignments for each prompt
- Changed `cache_prompts` to `true` for better performance

## Benefits

1. **Easy Customization**: Users can now edit prompts in `torri/prompts/` without touching Python code
2. **Better Maintainability**: Prompts are centralized and version-controlled separately
3. **Clear Documentation**: Each prompt file is self-documenting and easy to understand
4. **Consistent Format**: All prompts use the same `.format()` template syntax
5. **No Code Duplication**: Removed ~500 lines of hardcoded prompt strings

## Testing

All modified Python files passed syntax validation:
```bash
python3 -m py_compile src/utils/prompt_loader.py \
    src/harness/expert_agents.py \
    src/report_fixer.py \
    src/report_validator.py
```

## How to Modify Prompts

To change any prompt behavior, simply edit the corresponding `.txt` file in `torri/prompts/`:

```bash
# Example: Modify the GRB expert prompt
nano torri/prompts/grb_expert.txt

# The changes will be automatically picked up on next run
# (if cache_prompts is false, otherwise restart the service)
```

## Template Variables

Each prompt uses Python string formatting with these common variables:
- `{title}` - Paper title
- `{authors}` - Paper authors
- `{abstract}` - Paper abstract
- `{analysis}` - Previous analysis text
- `{attempt_num}` - Retry attempt number
- And more specific to each prompt type

See individual `.txt` files for the exact variables used.
