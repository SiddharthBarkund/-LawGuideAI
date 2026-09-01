import os
import re
import math
import collections
import json
from PyPDF2 import PdfReader
from .config import logger

class SimpleBM25:
    def __init__(self, corpus, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.corpus_size = len(corpus)
        
        self.doc_lens = []
        self.doc_freqs = []
        df = collections.defaultdict(int)
        
        for doc in corpus:
            words = self.tokenize(doc["text"])
            self.doc_lens.append(len(words))
            frequencies = collections.defaultdict(int)
            for word in words:
                frequencies[word] += 1
            self.doc_freqs.append(frequencies)
            for word in frequencies:
                df[word] += 1
                
        self.avg_doc_len = sum(self.doc_lens) / self.corpus_size if self.corpus_size > 0 else 0
        
        self.idf = {}
        for word, freq in df.items():
            self.idf[word] = math.log(1 + (self.corpus_size - freq + 0.5) / (freq + 0.5))

    def tokenize(self, text):
        return re.findall(r'[\w\u0900-\u097f]+', text.lower())

    def search(self, query_str, top_n=3, score_threshold=1.5):
        if not self.corpus:
            return []
        
        query_words = self.tokenize(query_str)
        if not query_words:
            return []
            
        scores = [0.0] * self.corpus_size
        for word in query_words:
            if word not in self.idf:
                continue
            idf_val = self.idf[word]
            for i in range(self.corpus_size):
                tf = self.doc_freqs[i].get(word, 0)
                if tf == 0:
                    continue
                doc_len = self.doc_lens[i]
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_len)
                scores[i] += idf_val * (numerator / denominator)
                
        ranked_indices = sorted(range(self.corpus_size), key=lambda idx: scores[idx], reverse=True)
        
        results = []
        for idx in ranked_indices[:top_n]:
            if scores[idx] < score_threshold:
                continue
            results.append({
                "text": self.corpus[idx]["text"],
                "source": self.corpus[idx]["source"],
                "page": self.corpus[idx]["page"],
                "score": scores[idx]
            })
        return results

# Module level search engine reference
law_search_engine = None

def build_or_load_data_index():
    global law_search_engine
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    possible_dirs = [
        os.path.join(current_dir, "..", "data"),
        os.path.join(current_dir, "data"),
    ]
    
    data_dir = None
    for d in possible_dirs:
        if os.path.exists(d):
            data_dir = d
            break
            
    if not data_dir:
        logger.warning("⚠️ Data directory not found. Law search RAG will be disabled.")
        return
        
    index_file = os.path.join(data_dir, "data_index.json")
    
    if os.path.exists(index_file):
        try:
            logger.info(f"📖 Loading law search index from cache: {index_file}")
            with open(index_file, 'r', encoding='utf-8') as f:
                corpus = json.load(f)
            law_search_engine = SimpleBM25(corpus)
            logger.info(f"✅ Loaded {len(corpus)} search index chunks.")
            return
        except Exception as e:
            logger.error(f"⚠️ Error loading search index: {e}. Will attempt to rebuild.")
            
    # If index cache not found or failed to load, check for PDF documents to build
    pdf_files = [f for f in os.listdir(data_dir) if f.endswith('.pdf')]
    if not pdf_files:
        logger.warning("⚠️ No PDFs found in data directory. Law search RAG will be disabled.")
        return
        
    logger.info("🔄 Index cache not found. Rebuilding search index...")
    corpus = []
    
    def clean(t):
        return re.sub(r'\s+', ' ', t).strip()
        
    def chunk(t, size=1200, overlap=200):
        if len(t) <= size:
            return [t]
        chks = []
        st = 0
        while st < len(t):
            nd = st + size
            if nd >= len(t):
                chks.append(t[st:])
                break
            sp_idx = t.rfind(' ', st + size - 100, nd)
            if sp_idx != -1:
                nd = sp_idx
            chks.append(t[st:nd].strip())
            st = nd - overlap
        return chks

    for filename in pdf_files:
        filepath = os.path.join(data_dir, filename)
        try:
            reader = PdfReader(filepath)
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if not text:
                    continue
                cleaned = clean(text)
                if not cleaned:
                    continue
                for chunk_idx, chk in enumerate(chunk(cleaned)):
                    corpus.append({
                        "text": chk,
                        "source": filename,
                        "page": i + 1,
                        "chunk_index": chunk_idx
                    })
        except Exception as err:
            logger.error(f"⚠️ Error reading {filename}: {err}")
            
    if corpus:
        try:
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(corpus, f, ensure_ascii=False, indent=2)
            law_search_engine = SimpleBM25(corpus)
            logger.info(f"✅ Rebuilt search index with {len(corpus)} chunks.")
        except Exception as e:
            logger.error(f"⚠️ Error saving search index cache: {e}")
