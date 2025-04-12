from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from model import process_document, query_document, summarize_document, model, validate_summary, validate_query_summary, query_section, extract_problem_statement_num_from_query  # Import model and validation functions
import os
import numpy as np
from typing import Optional, List, Dict
import uuid
import json
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
DOCUMENT_STORE_FILE = "document_store.json"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class DocumentStore:
    def __init__(self):
        self.documents = {}
        self.active_document_id = None
        self.load_documents()
        
    def load_documents(self):
        if os.path.exists(DOCUMENT_STORE_FILE):
            try:
                with open(DOCUMENT_STORE_FILE, 'r') as f:
                    data = json.load(f)
                    self.documents = data.get('documents', {})
                    self.active_document_id = data.get('active_document_id')
            except Exception as e:
                print(f"Error loading document store: {str(e)}")
                
    def save_documents(self):
        try:
            with open(DOCUMENT_STORE_FILE, 'w') as f:
                json.dump({
                    'documents': self.documents,
                    'active_document_id': self.active_document_id
                }, f)
        except Exception as e:
            print(f"Error saving document store: {str(e)}")
            
    def add_document(self, doc_data):
        doc_id = doc_data.get('id', str(uuid.uuid4()))
        doc_data['id'] = doc_id
        self.documents[doc_id] = doc_data
        if not self.active_document_id:
            self.active_document_id = doc_id
        self.save_documents()
        return doc_id
        
    def get_document(self, doc_id=None):
        if not doc_id:
            doc_id = self.active_document_id
        return self.documents.get(doc_id)
        
    def set_active_document(self, doc_id):
        if doc_id in self.documents:
            self.active_document_id = doc_id
            self.save_documents()
            return True
        return False
        
    def list_documents(self):
        return list(self.documents.values())
        
    def remove_document(self, doc_id):
        if doc_id in self.documents:
            file_path = self.documents[doc_id].get('path')
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Error removing file: {str(e)}")
            
            del self.documents[doc_id]
            
            if self.active_document_id == doc_id:
                self.active_document_id = next(iter(self.documents.keys())) if self.documents else None
                
            self.save_documents()
            return True
        return False

document_store = DocumentStore()

class DocumentResponse(BaseModel):
    id: str
    name: str
    size: Optional[int] = None
    upload_date: Optional[str] = None

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    file_path = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    processed = process_document(file_path)
    
    doc_id = document_store.add_document({
        'name': file.filename,
        'path': file_path,
        'size': len(content),
        'upload_date': str(datetime.datetime.now()),
        'chunks': processed["chunks"],
        'embeddings': processed["embeddings"].tolist(),
        'metadata': processed["metadata"],
        'sections': processed["sections"],
        'full_text': processed["full_text"]
    })
    
    return {"status": "success", "document_id": doc_id}

@app.get("/documents/{doc_id}/sections")
async def get_document_sections(doc_id: str):
    document = document_store.get_document(doc_id)
    
    if not document:
        raise HTTPException(404, "Document not found")
    
    if "sections" not in document:
        return {"sections": [{"title": "Document", "content": "Full document"}]}
    
    sections = [{"title": section["title"]} for section in document["sections"]]
    return {"sections": sections}

@app.get("/documents", response_model=List[DocumentResponse])
async def get_documents():
    docs = document_store.list_documents()
    return [{
        'id': doc.get('id', ''),
        'name': doc.get('name', 'Unnamed Document'),
        'size': doc.get('size'),
        'upload_date': doc.get('upload_date')
    } for doc in docs]

@app.post("/documents/{doc_id}/activate")
async def activate_document(doc_id: str):
    if document_store.set_active_document(doc_id):
        return {"status": "success"}
    raise HTTPException(404, "Document not found")

@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    if document_store.remove_document(doc_id):
        return {"status": "success"}
    raise HTTPException(404, "Document not found")

@app.post("/query")
async def query(
    prompt: str = Form(...), 
    doc_id: Optional[str] = Form(None),
    section: Optional[str] = Form(None)
):
    document = document_store.get_document(doc_id)
    
    if not document:
        raise HTTPException(400, "No document available")
    
    problem_num = extract_problem_statement_num_from_query(prompt)
    if problem_num and not section:
        section = f"Problem Statement {problem_num}"
    
    embeddings = np.array(document["embeddings"])
    
    metadata = document.get("metadata", [{}] * len(document["chunks"]))
    
    result = query_section(
        document["chunks"],
        embeddings,
        metadata,
        prompt,
        section
    )
    
    return {"result": result}

@app.get("/summary")
async def get_summary(doc_id: Optional[str] = None, max_length: int = 500, validate: bool = True):
    document = document_store.get_document(doc_id)
    
    if not document:
        raise HTTPException(400, "No document available")
    
    summary = summarize_document(document["full_text"], max_length=max_length)
    
    response = {"summary": summary}
    
    if validate:
        validation = validate_summary(summary, document["full_text"])
        response["validation"] = validation
    
    return response

@app.post("/query_summary")
async def query_summary(
    prompt: str = Form(...), 
    doc_id: Optional[str] = Form(None), 
    section: Optional[str] = Form(None),
    max_chunks: int = 3, 
    max_length: int = 500,
    validate: bool = Form(True)
):
    document = document_store.get_document(doc_id)
    
    if not document:
        raise HTTPException(400, "No document available")
    
    problem_num = extract_problem_statement_num_from_query(prompt)
    if problem_num and not section:
        section = f"Problem Statement {problem_num}"
    
    if section and "sections" in document:
        matched_section = None
        for sec in document["sections"]:
            sec_title = sec["title"].lower()
            if section.lower() in sec_title or (
                "section_num" in sec and 
                sec["section_num"] == problem_num
            ):
                matched_section = sec
                break
                
        if matched_section:
            focused_summary = summarize_document(matched_section["content"], max_length=max_length)
            
            response = {
                "summary": focused_summary,
                "source_section": matched_section["title"]
            }
            
            if validate:
                validation = validate_summary(focused_summary, matched_section["content"])
                response["validation"] = validation
                
            return response
        else:
            broader_match = None
            search_terms = [
                problem_num, 
                f"statement {problem_num}", 
                f"section {problem_num}"
            ]
            
            for sec in document["sections"]:
                sec_title = sec["title"].lower()
                for term in search_terms:
                    if term in sec_title:
                        broader_match = sec
                        break
                if broader_match:
                    break
            
            if broader_match:
                focused_summary = summarize_document(broader_match["content"], max_length=max_length)
                
                response = {
                    "summary": focused_summary,
                    "source_section": broader_match["title"]
                }
                
                if validate:
                    validation = validate_summary(focused_summary, broader_match["content"])
                    response["validation"] = validation
                    
                return response
    
    embeddings = np.array(document["embeddings"])
    
    metadata = document.get("metadata", [{}] * len(document["chunks"]))
    
    filtered_chunks = []
    filtered_embeddings = []
    
    if problem_num or section:
        target = problem_num or section
        query_terms = [
            f"problem statement {target}", 
            f"ps{target}", 
            f"problem {target}", 
            f"statement {target}", 
            target
        ]
        
        for i, meta in enumerate(metadata):
            section_title = meta.get("section", "").lower()
            
            for term in query_terms:
                if term in section_title:
                    filtered_chunks.append(document["chunks"][i])
                    filtered_embeddings.append(embeddings[i])
                    break
        
        if filtered_chunks:
            chunks_to_use = filtered_chunks
            embeddings_to_use = np.array(filtered_embeddings)
        else:
            chunks_to_use = document["chunks"]
            embeddings_to_use = embeddings
    else:
        chunks_to_use = document["chunks"]
        embeddings_to_use = embeddings
    
    prompt_embedding = model.encode([prompt])
    similarities = np.dot(embeddings_to_use, prompt_embedding.T).flatten()
    
    top_indices = np.argsort(similarities)[-max_chunks:][::-1]
    
    relevant_text = " ".join([chunks_to_use[i] for i in top_indices])
    
    focused_summary = summarize_document(relevant_text, max_length=max_length)
    
    response = {"summary": focused_summary}
    
    if validate:
        validation = validate_query_summary(
            focused_summary, 
            prompt, 
            chunks_to_use,
            embeddings_to_use
        )
        response["validation"] = validation
    
    return response

@app.get("/summary/section")
async def get_section_summary(
    doc_id: Optional[str] = None, 
    section: str = None,
    max_length: int = 500,
    validate: bool = True
):
    if not section:
        raise HTTPException(400, "No section specified")
        
    document = document_store.get_document(doc_id)
    
    if not document:
        raise HTTPException(400, "No document available")
        
    if "sections" not in document:
        raise HTTPException(400, "Document doesn't have section information")
    
    summary = summarize_section(document["sections"], section, max_length)
    
    response = {"summary": summary}
    
    if validate:
        section_content = ""
        for sec in document["sections"]:
            if section.lower() in sec["title"].lower():
                section_content = sec["content"]
                break
                
        if section_content:
            validation = validate_summary(summary, section_content)
            response["validation"] = validation
    
    return response

import datetime