# Guide to Updating twelve_labs_processor.py with Official SDK Workflows

## 1. Introduction

This document outlines key findings from the official Twelve Labs Python SDK documentation for index management, video uploading/indexing, and searching. It provides recommendations and a plan for refactoring `backend/app/core/video_agent/twelve_labs_processor.py` to align with these official SDK workflows, enhancing robustness and maintainability.

## 2. Official Twelve Labs SDK Workflows Summary

The following summarizes the standard methods for interacting with the Twelve Labs API using their Python SDK.

### 2.1. Index Management

Indexes are containers for your videos and their associated metadata. The `TwelveLabsClient` should expose `client.indexes`.

#### 2.1.1. Create an Index

*   **SDK Method**: `client.indexes.create()`
*   **Description**: Creates a new index.
*   **Signature**:
    ```python
    from twelvelabs import types

    def create(
        self,
        name: str,
        models: List[types.IndexModel], # e.g., [types.IndexModel(name="marengo2.6", options=["visual", "conversation"])]
        *,
        addons: Optional[List[str]] = None, # e.g., ["thumbnail"]
        **kwargs
    ) -> models.Index
    ```
*   **Key Parameters**:
    *   `name`: Unique name for the index.
    *   `models`: List of `types.IndexModel` objects specifying engine configurations.
*   **Returns**: A `models.Index` object representing the created index (contains `id`, `name`, etc.).

#### 2.1.2. Retrieve an Index

*   **SDK Method**: `client.indexes.retrieve()`
*   **Description**: Retrieves details of a specific index by its ID.
*   **Signature**:
    ```python
    def retrieve(self, id: str, **kwargs) -> models.Index
    ```
*   **Returns**: A `models.Index` object.

#### 2.1.3. List Indexes

*   **SDK Method**: `client.indexes.list()`
*   **Description**: Lists all indexes. Supports pagination.
*   **Returns**: A list of `models.Index` objects.

### 2.2. Video Uploading & Indexing (Tasks)

Video uploading and indexing are asynchronous operations managed as "tasks". The `TwelveLabsClient` should expose `client.tasks`.

#### 2.2.1. Create a Video Indexing Task

*   **SDK Method**: `client.tasks.create()`
*   **Description**: Uploads a video (from file or URL) and initiates indexing into a specified index. This is the primary method for uploading.
*   **Signature**:
    ```python
    from typing import Union, BinaryIO # At the top of your file

    def create(
        self,
        index_id: str,
        *,
        file: Union[str, BinaryIO, None] = None, # Path to local file or file-like object
        url: Optional[str] = None, # URL of the video
        enable_video_stream: Optional[bool] = None, # For HLS/MPEG-DASH
        **kwargs,
    ) -> models.Task
    ```
*   **Key Parameters**:
    *   `index_id`: The ID of the index to add the video to.
    *   `file` (for local uploads) or `url` (for remote videos).
*   **Returns**: A `models.Task` object. This object contains `id` (the task ID) and `status`. The actual `video_id` (which is different from the task ID) becomes available on the `Task` object once processing is complete and successful.

#### 2.2.2. Retrieve a Video Indexing Task

*   **SDK Method**: `client.tasks.retrieve()`
*   **Description**: Retrieves the details and status of a specific video indexing task by its task ID.
*   **Signature**:
    ```python
    def retrieve(self, id: str, **kwargs) -> models.Task # id here is the task_id
    ```
*   **Returns**: A `models.Task` object with current status (e.g., `pending`, `processing`, `ready`, `failed`).

#### 2.2.3. Wait for a Video Indexing Task to Complete

*   **SDK Method**: `task_object.wait_for_done()` (This is a method on an instance of `models.Task`)
*   **Description**: A helper method that polls the task status until it's completed (status is `ready` or `failed`).
*   **Signature**:
    ```python
    from typing import Callable # At the top of your file

    def wait_for_done(
        self, # This is a method of the Task object instance
        *,
        sleep_interval: float = 5.0, # Seconds between checks
        callback: Optional[Callable[[models.Task], None]] = None, # Optional callback for progress
        **kwargs,
    ) -> models.Task
    ```
*   **Returns**: The completed `models.Task` object.

### 2.3. Searching Videos

Once videos are indexed (task status is `ready`), they can be searched. The `TwelveLabsClient` should expose `client.search`.

#### 2.3.1. Make a Search Request

*   **SDK Method**: `client.search.query()`
*   **Description**: Performs a search across a specific index.
*   **Signature**:
    ```python
    from typing import List, Literal, Optional, Dict, Any # At the top of your file

    def query(
        self,
        index_id: str,
        options: List[Literal["visual", "audio", "conversation", "text_in_video", "logo"]],
        *,
        query_text: str = None,
        # ... other parameters like query_media_file, group_by, threshold, filter, page_limit, sort_option
        **kwargs
    ) -> models.SearchResult
    ```
*   **Key Parameters**:
    *   `index_id`: ID of the index to search within.
    *   `options`: List of search modalities.
    *   `query_text`: The textual search query.
*   **Returns**: A `models.SearchResult` object containing the search results.

## 3. Plan to Update `twelve_labs_processor.py`

The following steps outline the plan to refactor `process_video_for_twelve_labs` and related functions in `backend/app/core/video_agent/twelve_labs_processor.py` to use the official SDK workflows.

### 3.1. Ensure `TwelveLabsClient` is Aligned

*   **Verify**: Confirm that `app.core.twelve_labs.client.TwelveLabsClient` correctly initializes and exposes `self.client.indexes`, `self.client.tasks`, and `self.client.search` as per the SDK's structure. (Based on checkpoint summary, this was addressed).
    *   Example `TwelveLabsClient` structure:
        ```python
        # app/core/twelve_labs/client.py
        from twelvelabs import TwelveLabs as OfficialTwelveLabsClient
        from twelvelabs.models import Index as TwelveLabsIndexModel # For type hinting

        class TwelveLabsClient:
            def __init__(self, api_key: Optional[str] = None):
                # Simplified: direct use of official client
                self.client = OfficialTwelveLabsClient(api_key=api_key or os.environ.get("TWELVE_LABS_API_KEY"))
                self.indexes = self.client.indexes
                self.tasks = self.client.tasks
                self.search = self.client.search
                # Add other namespaces like embeddings if needed
        ```

### 3.2. Update Index Handling in `process_video_for_twelve_labs`

*   **List Indexes**:
    *   Replace custom logic for listing and finding indexes with `client.indexes.list()`.
    *   Iterate through the returned list to find an index by `name`.
    ```python
    # In process_video_for_twelve_labs
    indexes = client.indexes.list()
    index_id = None
    found_index = None
    for idx in indexes: # idx is a models.Index object
        if idx.name == DEFAULT_INDEX_NAME:
            found_index = idx
            index_id = idx.id # Access .id attribute
            break
    ```
*   **Create Index**:
    *   If the index is not found, use `client.indexes.create()`.
    *   Ensure `models` parameter uses `types.IndexModel` and correct `options`.
    ```python
    from twelvelabs import types # Add to imports in twelve_labs_processor.py

    if not found_index:
        logger.info(f"Index '{DEFAULT_INDEX_NAME}' not found, creating it.")
        index_models_config = [
            types.IndexModel(
                name="marengo2.6", # Confirm latest/best engine
                options=[
                    types.VIDEO_INDEXING_OPTIONS_VISUAL,
                    types.VIDEO_INDEXING_OPTIONS_CONVERSATION,
                    types.VIDEO_INDEXING_OPTIONS_TEXT_IN_VIDEO,
                    types.VIDEO_INDEXING_OPTIONS_LOGO,
                ]
            )
        ]
        addons_config = ["thumbnail"] # If needed
        
        new_index_obj = client.indexes.create(
            name=DEFAULT_INDEX_NAME,
            models=index_models_config,
            addons=addons_config
        )
        index_id = new_index_obj.id # Access .id attribute
        logger.info(f"Created new index with ID: {index_id}")
    ```

### 3.3. Refactor Video Upload and Processing Logic

This is the most significant change. Replace `client.upload_video`, `client.check_processing_started`, and `client.check_processing_complete` with the SDK's task-based workflow.

*   **Upload Video (Create Task)**:
    *   Use `client.tasks.create(index_id=index_id, file=video_path)` to upload the video. This returns a `task` object.
    *   The `task.id` is the ID for monitoring this specific upload/indexing job.
    *   The actual `video_id` (for searching later) will be available on the `task` object (`task.video_id`) *after* the task status is `ready`.
    ```python
    # In process_video_for_twelve_labs, after getting index_id
    logger.info(f"Uploading video '{video_path}' to index '{index_id}' by creating a task.")
    task = client.tasks.create(index_id=index_id, file=video_path)
    logger.info(f"Task created with ID: {task.id}, current status: {task.status}")
    
    # Store task_id for potential later status checks if needed,
    # but primary flow will wait for completion.
    ```

*   **Wait for Processing Completion**:
    *   Use the `task.wait_for_done()` method on the returned task object. This blocks until the task is `ready` or `failed`.
    *   Implement a callback for logging progress if desired.
    ```python
    def log_task_progress(updated_task: models.Task): # Define this callback
        logger.info(f"Task {updated_task.id} status: {updated_task.status}, progress: {updated_task.process.get('percentage', 0) if updated_task.process else 'N/A'}%")

    logger.info(f"Waiting for task {task.id} to complete...")
    try:
        # task.wait_for_done() will raise an exception on timeout by default if not handled
        # The SDK's default timeout for wait_for_done might be long.
        # Consider wrapping with asyncio.wait_for for your own timeout if needed,
        # or handle SDK's timeout exception.
        # For now, rely on its internal polling.
        completed_task = task.wait_for_done(sleep_interval=check_interval, callback=log_task_progress)
        
        if completed_task.status == "ready":
            logger.info(f"Task {completed_task.id} completed successfully. Video ID: {completed_task.video_id}")
            # Store mapping using completed_task.video_id
            await store_twelve_labs_mapping(
                # ...
                twelve_labs_video_id=completed_task.video_id, # IMPORTANT
                status="ready"
            )
            # Proceed
        else: # e.g., "failed"
            error_msg = f"Video processing task {completed_task.id} failed with status: {completed_task.status}."
            if completed_task.error_message: # Check if SDK provides error message on task
                 error_msg += f" Details: {completed_task.error_message}"
            logger.error(error_msg)
            await update_twelve_labs_status(
                video_url=video_url, user_id=user_id, status="failed", error_message=error_msg
            )
            return False, error_msg
            
    except Exception as e: # Catch potential exceptions from wait_for_done (e.g. SDK's timeout)
        logger.error(f"Error waiting for task {task.id} to complete: {e}")
        await update_twelve_labs_status(
            video_url=video_url, user_id=user_id, status="failed", error_message=str(e)
        )
        return False, f"Error during video processing: {e}"
    ```

*   **Database Mapping**:
    *   The `twelve_labs_video_id` to store in Firestore is `completed_task.video_id`, available *after* the task is `ready`.
    *   Update status to `processing` when task is created, then `ready` or `failed` after `wait_for_done`.

### 3.4. Remove Obsolete Logic

*   Delete `client.upload_video`, `client.check_processing_started`, `client.check_processing_complete` from your custom `TwelveLabsClient` if they were custom implementations.
*   Remove the manual polling loop in `process_video_for_twelve_labs` as `task.wait_for_done()` handles this.
*   The `check_processing_status` function might become obsolete or need significant refactoring if it's intended for out-of-band status checks (it would now use `client.tasks.retrieve(task_id)`).

### 3.5. Implement Search Functionality (New or Update Existing)

*   If search functionality is part of `twelve_labs_processor.py` or a related module:
    *   Use `client.search.query(index_id=index_id, query_text="your query", options=["visual", "conversation"])`.
    *   Ensure the `index_id` and `video_id` (from search results) are correctly used.

### 3.6. Error Handling and Timeouts

*   The `task.wait_for_done()` method might have its own timeout mechanisms or raise exceptions. Review SDK documentation for `TwelveLabsTimeoutError` or similar.
*   Wrap calls to the SDK in `try...except` blocks to catch potential API errors (`APIError` from `twelvelabs.errors`) or network issues.
*   Your `max_wait_time` can still be relevant if you want an overall timeout for the `process_video_for_twelve_labs` function, potentially using `asyncio.wait_for` around the `task.wait_for_done()` call if `wait_for_done` itself is blocking or doesn't offer a configurable timeout parameter that suits your needs.

## 4. Checklist for Updating `twelve_labs_processor.py`

1.  [ ] **Backup**: Create a backup or a new branch for `twelve_labs_processor.py` before making changes.
2.  [ ] **Update `TwelveLabsClient`**: Ensure `client.py` correctly uses and exposes `indexes`, `tasks`, and `search` namespaces from the official SDK.
3.  [ ] **Imports**: Add necessary imports to `twelve_labs_processor.py` (e.g., `from twelvelabs import types`, `from twelvelabs import models` for type hinting `models.Task`).
4.  [ ] **Index Listing**: Modify index listing to use `client.indexes.list()` and access attributes like `idx.name`, `idx.id`.
5.  [ ] **Index Creation**: Modify index creation to use `client.indexes.create()` with `types.IndexModel`.
6.  [ ] **Video Upload (Task Creation)**: Replace current upload logic with `client.tasks.create()`.
7.  [ ] **Task Monitoring**: Replace manual status polling with `task_object.wait_for_done()`.
    *   [ ] Implement `log_task_progress` callback (optional but recommended).
8.  [ ] **Database Updates**:
    *   Store `task.id` initially if needed for external monitoring.
    *   Update Firestore with `status="processing"` after task creation.
    *   After `wait_for_done()`, use `completed_task.video_id` for `twelve_labs_video_id` in Firestore.
    *   Update status to `ready` or `failed` based on `completed_task.status`.
9.  [ ] **Error Handling**: Enhance error handling for SDK calls, especially around `wait_for_done()`.
10. [ ] **Remove Obsolete Code**: Delete old custom methods from `TwelveLabsClient` and the manual polling loop from `process_video_for_twelve_labs`.
11. [ ] **Refactor `check_processing_status`**: If this function is still needed, update it to use `client.tasks.retrieve(task_id)`. It will need the `task_id` which should be stored during task creation.
12. [ ] **Testing**:
    *   [ ] Test index creation for a new index.
    *   [ ] Test finding an existing index.
    *   [ ] Test video upload and successful processing (`ready` state).
    *   [ ] Test handling of video processing failure (`failed` state).
    *   [ ] Test search functionality (if applicable to this file).
13. [ ] **Review and Refine**: Review logging messages for clarity and completeness.

This plan provides a structured approach to refactoring your Twelve Labs integration.
