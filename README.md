# ChabotAgentProject

Absolutely 👍 Here’s a **crisp, professional README description** for your chatbot project — based on the details you shared earlier (multimodal chatbot, image-based search, FastAPI backend, React frontend, Gemini LLM, Milvus + OpenSearch retrieval, etc.).

You can paste this directly into your `README.md` file 👇

---

# 🧠 ChabotAgentProject — Multimodal AI Chatbot with Image-Based Search

A full-stack **multimodal chatbot platform** that combines text and image understanding using advanced LLMs and vector search. The system enables users to chat naturally, upload images, and retrieve contextually relevant information or images — all in a sleek, responsive web interface.

---

## 🚀 Features

* 💬 **LLM-Powered Chat** – Real-time conversational AI using Google **Gemini** for contextual and multimodal responses.
* 🖼️ **Image-Based Search** – Upload an image to find visually and semantically similar results via **CLIP** embeddings stored in **Milvus**.
* 🔍 **Hybrid Retrieval** – Combines **semantic vector search** (Milvus) with **keyword search** (OpenSearch) for precise and grounded responses.
* ⚡ **FastAPI Backend** – Handles LLM orchestration, embedding generation, and API routing efficiently.
* 🧩 **Scalable Ingestion Pipeline** – Automatic document and image preprocessing, embedding, and multi-threaded indexing.
* 🖥️ **Modern Frontend** – Built with **React + TypeScript**, featuring chat history, typing animation, drag-and-drop image uploads, and responsive UI.
* 🧠 **Structured Output Parsing** – Normalizes LLM responses into clean JSON for easy frontend rendering.

---

## 🏗️ Tech Stack

**Frontend:** React, TypeScript, Redux, Framer Motion
**Backend:** FastAPI, Python, uvicorn
**AI / Search:** Google Gemini API, CLIP (PyTorch), Milvus, OpenSearch, llama_index
**Storage / Utilities:** PIL, ThreadPoolExecutor, JSON, REST APIs

---

## ⚙️ Architecture Overview

```
React Frontend  ↔  FastAPI Gateway  ↔  LLM + Retrieval Engine
                       │
              ┌────────┴────────┐
              │                 │
         Milvus VectorDB   OpenSearch Index
              │                 │
           CLIP Embeddings   Keyword Search
```

---

## 💻 Getting Started

```bash
# Clone repository
git clone git@github.com:GuptaDevansh-2004/ChabotAgentProject.git
cd ChabotAgentProject

# Backend setup
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend setup
cd ../frontend
npm install
npm run dev
```

Then open `http://localhost:5173` to interact with the chatbot.

---

## 📷 Example Use Cases

* Ask questions about uploaded documents or images.
* Search for visually similar images using image embeddings.
* Retrieve accurate answers grounded in indexed data.
* Extend with new models, retrievers, or file types.
