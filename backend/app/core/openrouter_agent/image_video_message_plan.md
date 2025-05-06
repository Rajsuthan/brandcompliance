# Plan: Adding Images to Messages for Final Answer Generation (Finalized & Executed)

## 1. Context and Objective

- [x] **All images are removed from the messages before sending them for final answer generation (already implemented).**
- [x] **For image analysis:** After removing all images, add the relevant image (as base64) from the process function params to the messages, using the OpenAI image input format.
- [x] **For video analysis:** After removing all images, add all frame images (as base64) from the process function params to the messages, using the OpenAI image input format.

---

## 2. Detection of Analysis Type

- [x] **Where:** In the function that prepares the messages for final answer generation (`process` in `native_agent.py`).
- [x] **How:** If `image_base64` is present, it's image compliance. If `frames` is present, it's video compliance.

---

## 3. Extraction of Base64 Images

- [x] **For Image Analysis:** Use the `image_base64` string from params.
- [x] **For Video Analysis:** Use the list of frames from params, each frame should have an `image_data` key containing the base64 string.

---

## 4. OpenAI Image Message Format

- [x] **Format:**  
  OpenAI expects images in the message content as:
    ```json
    {
      "type": "image_url",
      "image_url": {
        "url": "data:image/jpeg;base64,....",
        "detail": "high" // or "low" depending on size
      }
    }
    ```
  For multiple images, each should be a separate message content block (or part of a list in a single message).

---

## 5. Insertion into Messages

- [x] **Where to Insert:** After appending previous messages (with all images removed) to `messages_for_completion` and **before** appending the final user prompt.
- [x] **How to Insert:**  
  - For image analysis: Append a message with content as a list containing a single image_url object (with the correct detail level).
  - For video analysis: For each frame, append a message with content as a list containing a single image_url object (with the correct detail level).

---

## 6. Edge Case Handling

- [x] **Missing Images:** If `image_base64` or any frame's `image_data` is missing, log a warning and skip.
- [x] **Empty Frame List:** If the frame list is empty for video, log a warning and proceed.
- [x] **Invalid Base64:** Validate that the base64 string is not empty and is a valid image (optional, but recommended for robustness).

---

## 7. Code Placement and Structure

- [x] **Where:** In the `process` function of `OpenRouterAgent` in `native_agent.py`, after appending previous messages (with images removed) to `messages_for_completion` and before appending the final user prompt.
- [x] **How:** Logic checks for `image_base64` or `frames` and appends the image(s) in the correct OpenAI format.

---

## 8. Testing and Validation

- [x] **Unit Tests:**  
  - Test with image analysis: ensure the single image is added in the correct format.
  - Test with video analysis: ensure all frame images are added in order and in the correct format.
  - Test with missing/empty/invalid images: ensure graceful handling.
- [x] **Integration Test:**  
  - Run through the full pipeline to ensure the final answer generation receives the messages with the correct image blocks.

---

## 9. Documentation

- [x] **Code comments and docstrings** have been updated to explain the new logic.
- [x] **Params structure** for both image and video analysis is documented in the code and this plan.

---

## Summary Table

| Step                | Image Analysis                | Video Analysis                        |
|---------------------|------------------------------|---------------------------------------|
| Detect type         | `image_base64` param         | `frames` param                        |
| Extract images      | `image_base64`               | `frame["image_data"]` for each frame  |
| Remove old images   | Already implemented          | Already implemented                   |
| Add new images      | 1 image_url message          | N image_url messages (one per frame)  |
| Insert position     | After previous messages, before final user prompt | After previous messages, before final user prompt |
| Format              | OpenAI image_url format      | OpenAI image_url format               |

---

## ✅ Status: Fully Executed

- [x] The plan has been fully implemented in `backend/app/core/openrouter_agent/native_agent.py`.
- [x] The process function now inserts the correct image(s) for both image and video compliance analysis, after removing previous images and before the final user prompt, in the required OpenAI format.
- [x] All requirements and edge cases from the plan have been addressed.
