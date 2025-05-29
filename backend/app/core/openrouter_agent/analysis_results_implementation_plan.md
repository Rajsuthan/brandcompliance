# Implementation Plan: Sending Analysis Results to Frontend

## Background
As part of the OpenRouter migration, we need to implement a feature to send the array of analysis sections to the frontend after the attempt_completion tool stream is sent.

## Current Implementation
- Analysis sections are defined in the `ANALYSIS_SECTIONS` constant in `native_agent.py`
- Results from each section are stored in the `section_results` dictionary
- These results are added to the final result as `final_result['analysis_sections'] = section_results`
- Currently, only the `attempt_completion` tool stream is sent to the frontend with the final result

## Requirements
- Send the analysis sections array to the frontend after sending the attempt_completion tool stream
- Create a new stream called `analysis_results` that contains the section results array
- Ensure backward compatibility with existing frontend code

## Implementation Steps

### 1. Identify the Location for Implementation
- The code change should be made in `backend/app/core/openrouter_agent/native_agent.py`
- The exact location is after sending the `attempt_completion` stream in the `process` method

### 2. Create Analysis Results Stream
- Add code to send a new stream event immediately after the `attempt_completion` stream
- Use the existing `on_stream` callback mechanism
- Format the analysis results as a properly structured event

### 3. Implementation Details
```python
# After sending the attempt_completion event:
if self.message_handler.on_stream:
    # First send the completion notification (existing code)
    await self.message_handler.on_stream({
        "type": "text",
        "content": f"🎉 Compliance analysis complete! Processing time: {multi_section_duration:.1f}s"
    })
    
    # Prepare and send the complete event (existing code)
    complete_event_content = json.dumps({
        "tool_name": "attempt_completion",
        "task_detail": "Final compliance analysis",
        "tool_result": final_result
    })
    
    # Send the complete event (existing code)
    await self.message_handler.on_stream({
        "type": "complete",
        "content": complete_event_content
    })
    
    # NEW CODE: Send analysis results as a separate stream
    analysis_results_content = json.dumps({
        "tool_name": "analysis_results",
        "task_detail": "Section-by-section analysis results",
        "tool_result": section_results
    })
    
    # Send the analysis results event
    await self.message_handler.on_stream({
        "type": "complete",
        "content": analysis_results_content
    })
```

### 4. Error Handling
- Ensure proper error handling in case the section_results dictionary is empty or invalid
- Log any issues that might occur during the streaming process

### 5. Testing Plan
- Test the implementation with various analysis scenarios
- Verify that both streams (attempt_completion and analysis_results) are sent correctly
- Confirm that the frontend receives and can parse the analysis_results stream

### 6. Frontend Integration
- Update frontend code to handle the new analysis_results stream
- Display the section-by-section results in the UI as needed

## Alternative Approaches Considered

### Alternative 1: Include Analysis Sections in attempt_completion Only
- Simply continue with the current approach where analysis_sections are included in the final_result
- Pros: No changes needed to backend streaming logic
- Cons: Less explicit separation of concerns, might make frontend processing more complex

### Alternative 2: Progressive Streaming of Analysis Results
- Stream each section result as it completes rather than at the end
- Pros: More real-time feedback to users during long analyses
- Cons: More complex implementation, requires significant frontend changes

## Decision
We've chosen to implement a dedicated analysis_results stream after the attempt_completion stream because:
1. It provides a clear separation of concerns
2. It allows for explicit handling of analysis results on the frontend
3. It requires minimal changes to the existing codebase
4. It maintains compatibility with the existing streaming architecture
