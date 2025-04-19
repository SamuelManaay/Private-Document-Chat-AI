import os
import re
from flask import Flask, request, render_template
from whoosh.index import create_in
from whoosh.fields import TEXT, ID, Schema
from whoosh.qparser import MultifieldParser, OrGroup
from whoosh.analysis import StemmingAnalyzer
from whoosh import scoring
import spacy
from collections import Counter
from transformers import pipeline
from docx import Document

# PDF handling
try:
    import fitz
    PDF_ENGINE = "pymupdf"
    fitz.TOOLS.mupdf_warnings()
except ImportError:
    try:
        import pdfplumber
        PDF_ENGINE = "pdfplumber"
    except ImportError:
        from PyPDF2 import PdfReader
        PDF_ENGINE = "pypdf2"

# Flask app setup
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
UPLOAD_FOLDER = 'documents'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# NLP setup
try:
    nlp = spacy.load("en_core_web_lg")
except:
    import spacy.cli
    spacy.cli.download("en_core_web_lg")
    nlp = spacy.load("en_core_web_lg")

# Load Flan-T5 model
t5_generator = pipeline("text2text-generation", model="google/flan-t5-base")

# Globals
ix = None
current_filename = ""
full_text = ""
metadata = {}
document_sections = []

class DocumentProcessor:
    def __init__(self):
        self.analyzer = StemmingAnalyzer()
        self.section_min_length = 200
        self.section_max_length = 1000

    def extract_text(self, filepath):
        text = ""
        try:
            if filepath.lower().endswith('.pdf'):
                if PDF_ENGINE == "pymupdf":
                    with fitz.open(filepath) as doc:
                        for page in doc:
                            text += page.get_text("text", sort=True) + "\n"
                        global metadata
                        if doc.metadata:
                            metadata = {k: v for k, v in doc.metadata.items() if v}
                elif PDF_ENGINE == "pdfplumber":
                    with pdfplumber.open(filepath) as pdf:
                        text = "\n".join([page.extract_text() or "" for page in pdf.pages])
                        metadata = getattr(pdf, 'metadata', {})
                else:
                    reader = PdfReader(filepath)
                    text = "\n".join([page.extract_text() or "" for page in reader.pages])
                    metadata = {k[1:]: v for k, v in reader.metadata.items() if v}
            elif filepath.lower().endswith('.docx'):
                doc = Document(filepath)
                text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
                metadata['title'] = os.path.basename(filepath)
            else:
                return ""
            text = re.sub(r'\s+', ' ', text).strip()
            return text
        except Exception as e:
            print(f"Extraction error: {e}")
            return ""

    def segment_document(self, text):
        doc = nlp(text)
        sections = []
        current = []
        current_len = 0
        for sent in doc.sents:
            s = sent.text.strip()
            if not s:
                continue
            l = len(s)
            if current_len + l > self.section_max_length or (s.endswith(':') and len(s) < 100):
                section = ' '.join(current)
                if len(section) >= self.section_min_length:
                    sections.append(section)
                current = []
                current_len = 0
            current.append(s)
            current_len += l
        if current:
            section = ' '.join(current)
            if len(section) >= self.section_min_length:
                sections.append(section)
        return sections

processor = DocumentProcessor()

def create_search_index(sections):
    schema = Schema(
        id=ID(stored=True),
        content=TEXT(stored=True, analyzer=processor.analyzer, phrase=True),
        context=TEXT(analyzer=processor.analyzer),
        entities=TEXT(analyzer=processor.analyzer),
        keywords=TEXT(analyzer=processor.analyzer)
    )
    if not os.path.exists("search_index"):
        os.mkdir("search_index")
    ix = create_in("search_index", schema)
    writer = ix.writer()
    for i, section in enumerate(sections):
        doc = nlp(section)
        keywords = [t.lemma_ for t in doc if t.pos_ in ('NOUN', 'VERB', 'ADJ') and not t.is_stop]
        entities = [ent.text for ent in doc.ents]
        context_sents = [sent.text for sent in doc.sents][:3]
        writer.add_document(
            id=str(i),
            content=section,
            context=" ".join(context_sents),
            entities=" ".join(entities),
            keywords=" ".join(keywords)
        )
    writer.commit()
    return ix

def flan_t5_generate_answer(question, context):
    prompt = f"Answer the question based on the context.\n\nContext:\n{context}\n\nQuestion: {question}"
    response = t5_generator(prompt, max_length=200, num_return_sequences=1, do_sample=False)
    return response[0]['generated_text']

@app.route('/', methods=['GET', 'POST'])
def index():
    global ix, current_filename, full_text, metadata, document_sections
    if request.method == 'POST':
        if 'file' not in request.files or request.files['file'].filename == '':
            return render_template("index.html", message=("No file selected", "error"), processed=False)
        file = request.files['file']
        if file and (file.filename.lower().endswith('.pdf') or file.filename.lower().endswith('.docx')):
            try:
                filepath = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(filepath)
                current_filename = file.filename
                metadata = {}
                full_text = processor.extract_text(filepath)
                if not full_text.strip():
                    return render_template("index.html", message=("Error: Could not extract text", "error"), processed=False)
                document_sections = processor.segment_document(full_text)
                ix = create_search_index(document_sections)
                doc_summary = nlp(full_text[:5000])
                keywords = [chunk.text for chunk in doc_summary.noun_chunks]
                top_keywords = Counter(keywords).most_common(5)
                metadata['keywords'] = ", ".join([kw[0] for kw in top_keywords])
                return render_template("index.html", message=(f"'{current_filename}' processed successfully", "success"),
                                       processed=True, doc_title=metadata.get('title', current_filename),
                                       doc_author=metadata.get('author', 'Unknown'),
                                       doc_keywords=metadata.get('keywords', ''))
            except Exception as e:
                return render_template("index.html", message=(f"Error processing file: {str(e)}", "error"), processed=False)
        else:
            return render_template("index.html", message=("Only PDF and Word (.docx) files are supported", "error"), processed=False)
    return render_template("index.html", processed=False)

@app.route('/ask', methods=['POST'])
def ask():
    global ix, current_filename, full_text
    question = request.form.get('question', '').strip()
    if not question:
        return render_template("index.html", answer="Please enter a question", question="", processed=True,
                               current_filename=current_filename)
    context = ""
    if ix:
        with ix.searcher(weighting=scoring.BM25F()) as searcher:
            query = MultifieldParser(["content", "context", "entities", "keywords"], ix.schema, group=OrGroup).parse(question)
            hits = list(searcher.search(query, limit=3))
            for hit in hits:
                context += hit['content'] + "\n"

    if not context:
        return render_template("index.html", answer="Sorry, I couldn't find relevant information in the document.",
                               question=question, processed=True, current_filename=current_filename)

    answer = flan_t5_generate_answer(question, context)

    return render_template("index.html", answer=answer, question=question, processed=True,
                           current_filename=current_filename,
                           doc_title=metadata.get('title', current_filename),
                           doc_author=metadata.get('author', 'Unknown'),
                           doc_keywords=metadata.get('keywords', ''))

if __name__ == '__main__':
    app.run(debug=True, port=5001)
