# OpenRouter Native Tool Call Migration Plan

This document outlines the step-by-step plan for migrating our current XML-based tool calling implementation to OpenRouter's native tool calling mechanism.

## Background

Currently, our OpenRouter agent uses a custom XML-based approach to extract tool calls from model responses. OpenRouter provides native support for tool calls in a structured JSON format that is compatible with the OpenAI SDK. This migration will simplify our codebase, improve reliability, and ensure compatibility with future updates.

## Migration TODOs

### Phase 1: Update Dependencies and Configuration (1 day)

- [x] Update or add OpenAI SDK dependency to requirements.txt
- [x] Configure OpenAI client with OpenRouter base URL
- [x] Update initialization in agent.py to use OpenAI client
- [x] Create a new branch for this migration

### Phase 2: Update Tool Definition Format (1 day)

- [x] Review current `convert_tool` function to ensure compatibility
- [x] Update tool schema definitions with OpenRouter format
- [x] Create folder structure for tool definitions
- [x] Remove image_base64/images_base64 parameters from schemas (these will be injected during execution)
- [ ] Create test cases for tool definitions
- [ ] Verify tool definitions work with all supported models

### Phase 3: Replace XML Extraction with Native Parsing (2 days)

- [x] Create new `process_tool_calls` method to handle structured tool calls
- [x] Update `process` method to use native tool call objects
- [x] Remove `extract_xml_tool_call` method and related XML parsing
- [x] Update error handling for tool call processing
- [x] Add support for multiple tool calls in a single response

### Phase 4: Update the Agentic Loop (2-3 days)

- [x] Refactor the main agentic loop to use structured tool calls
- [x] Update message handling to include tool results in proper format
- [x] Implement proper tool call ID tracking
- [x] Update iteration and completion logic
- [ ] Add support for parallel tool execution (if needed)

### Phase 5: Update Streaming Logic (1-2 days)

- [x] Update streaming to handle native tool calls
- [x] Modify stream event types to reflect tool call structure
- [x] Update streaming error handling
- [x] Ensure compatibility with streaming timeouts and model switching

### Phase 6: Clean Up Legacy XML-Related Code (1 day)

- [x] Remove XML formatting guidance in prompt_manager.py
- [x] Remove XML parsing utilities (including `extract_xml_tool_call` method)
- [x] Update documentation to reflect new approach
- [x] Remove XML-specific error handling

### Phase 7: Update Tests (1-2 days)

- [ ] Update existing tests to use new tool call format
- [ ] Create new tests for native tool call functionality
- [ ] Test with various models (Claude, GPT, etc.)
- [ ] Add tests for error cases and edge conditions

### Phase 8: UI and Frontend Updates (if needed) (1-2 days)

- [ ] Update any frontend components that expect XML-formatted tool calls
- [ ] Ensure UI correctly displays tool calls and results
- [ ] Update visualizations for tool execution flow

### Phase 9: Documentation and Knowledge Transfer (1 day)

- [ ] Update internal documentation
- [ ] Create examples for common use cases
- [ ] Document any breaking changes
- [ ] Schedule knowledge transfer session with team

## Code Examples

### Current XML-based Approach

```python
# Extract tool calls from text
tool_tag, tool_input = self.extract_xml_tool_call(full_content)
if tool_tag and tool_input:
    # Execute tool and handle results
    tool_func = get_tool_function(tool_tag)
    tool_result = await tool_func(tool_input)
    # Send tool result as new user message
    await self.add_message("user", tool_result_message)
```

### New Native Tool Call Approach

```python
# Process tool calls from structured response
if response.choices[0].message.tool_calls:
    for tool_call in response.choices[0].message.tool_calls:
        tool_name = tool_call.function.name
        tool_args = json.loads(tool_call.function.arguments)
        
        # Execute tool
        tool_func = get_tool_function(tool_name)
        tool_result = await tool_func(tool_args)
        
        # Add tool result as a tool message
        await self.add_message("tool", {
            "tool_call_id": tool_call.id,
            "name": tool_name,
            "content": json.dumps(tool_result)
        })
```

## Testing Strategy

1. Create parallel implementation first to avoid breaking existing functionality
2. Add comprehensive tests for each component
3. Test with various models to ensure compatibility
4. Perform integration testing with the full system

## Rollback Plan

If issues are encountered during implementation or deployment:

1. Revert to the XML-based implementation
2. Document specific issues encountered
3. Create targeted fixes for those issues
4. Re-attempt migration with updated approach

## Timeline

- Total estimated time: 10-14 days
- Critical path: Phases 3 and 4 (replace XML extraction and update agentic loop)
- Suggested parallel work: Phase 7 (tests) can begin alongside Phase 2 (tool definition)
