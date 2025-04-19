# 🔒 Private Document Chat AI

A private, offline-friendly Q&A web app that lets you upload **PDF or Word (.docx)** documents and ask natural language questions about them — all through a clean, **ChatGPT-style** chat interface.

Powered by:
- 🤖 [Flan-T5](https://huggingface.co/google/flan-t5-base) for natural question answering
- 📚 [spaCy](https://spacy.io/) for text processing
- 🔍 [Whoosh](https://pypi.org/project/Whoosh/) for fast document indexing and search
- 🧠 Purely local, no data leaves your machine.

---

## 🧰 Features

- 📁 Upload and process `.pdf` or `.docx` documents
- 💬 Ask questions in a chat-like interface
- 🧠 AI answers based on the most relevant parts of the document
- 🔐 100% local and private — no cloud APIs
- 🧭 Smart sectioning + semantic search for accurate answers
- 🖥️ Works on CPU

---

## 🚀 Getting Started

### 1. Clone the Repo or Copy the Files

```bash
git clone https://github.com/yourname/private-doc-chat-ai
cd private-doc-chat-ai
```

Or just download the code.

---

### 2. Install Dependencies

It's recommended to use a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

Then install:

```bash
pip install -r requirements.txt
```

If you don’t have a `requirements.txt`, install manually:

```bash
pip install flask whoosh spacy transformers torch python-docx pymupdf
python -m spacy download en_core_web_lg
```

---

### 3. Run the App

```bash
python app.py
```

Visit [http://localhost:5001](http://localhost:5001) in your browser.

---

## 🖼 UI Preview

- Upload bar at the top
- Chat interface below
- Each question appears as a chat bubble, followed by the AI's response

---

## 🛡 Privacy

- All document processing and AI inference happens **locally**
- No internet connection is required after models are downloaded
- Your data never leaves your machine

---

## 📦 File Structure

```
├── app.py               # Flask backend
├── index.html           # Frontend (chat UI)
├── documents/           # Uploaded files (created automatically)
├── search_index/        # Temporary Whoosh index
└── README.md            # This file
```

---

## 🤖 Model Info

This app uses:

- **`google/flan-t5-base`** via Hugging Face Transformers
- You can change the model to `flan-t5-small` if you want faster performance

To switch:

```python
t5_generator = pipeline("text2text-generation", model="google/flan-t5-small")
```

---

## 📌 To Do / Ideas

- ✅ Chat-like UI ✅
- [ ] Multi-turn memory support
- [ ] Document summarization before chat
- [ ] Export Q&A chat log

---

## 📃 License

MIT — free for personal and commercial use.

---

## ✨ Credits

Built by Samuel Mana-ay  
Powered by Open Source AI 🧠
