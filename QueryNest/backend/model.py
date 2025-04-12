from sentence_transformers import SentenceTransformer
from transformers import pipeline
import numpy as np
import torch
import re
import fitz

model = SentenceTransformer('all-MiniLM-L6-v2')
qa_pipeline = pipeline("question-answering", model="deepset/roberta-base-squad2")
summarizer = pipeline("summarization", model="facebook/bart-large-cnn", device="cpu")

try:
    import nltk
    nltk.download('punkt', quiet=True)
except:
    print("Note: NLTK punkt download failed. Will use fallback methods.")

def process_document_with_sections(file_path: str):
    text = extract_text(file_path)
    sections = detect_sections(text)
    
    all_chunks = []
    all_embeddings = []
    all_metadata = []
    
    for section in sections:
        section_chunks = chunk_text(section["content"])
        
        for chunk in section_chunks:
            all_chunks.append(chunk)
            all_metadata.append({
                "section": section["title"],
                "section_content": section["content"]
            })
    
    all_embeddings = model.encode(all_chunks)
            
    return {
        "chunks": all_chunks,
        "embeddings": all_embeddings,
        "metadata": all_metadata,
        "sections": sections,
        "full_text": text
    }

def extract_text(file_path: str) -> str:
    try:
        with fitz.open(file_path) as doc:
            text = " ".join(page.get_text() for page in doc)
            text = re.sub(r'\s+', ' ', text).strip()
            text = ''.join(c for c in text if c.isprintable() or c.isspace())
            return text
    except Exception as e:
        print(f"Error extracting text: {str(e)}")
        return ""

def chunk_text(text: str, chunk_size=500) -> list[str]:
    if not text:
        return []
    
    words = text.split()
    chunks = [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
    return chunks

def query_document(chunks: list[str], embeddings: np.ndarray, prompt: str) -> str:
    if not chunks or len(chunks) == 0:
        return "No document content to search."
        
    prompt_embedding = model.encode([prompt])
    similarities = np.dot(embeddings, prompt_embedding.T).flatten()
    best_chunk_idx = np.argmax(similarities)
    
    result = qa_pipeline(
        question=prompt,
        context=chunks[best_chunk_idx],
        max_answer_len=2000
    )
    return result["answer"]

def clean_text_for_summarization(text):
    text = re.sub(r'\s+', ' ', text).strip()
    
    text = text.replace('\u2022', '*')
    
    if text and not text.endswith(('.', '!', '?')):
        text += '.'
    
    return text

def simple_split_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s for s in sentences if len(s.strip()) > 0]

def extract_key_sentences(text, num_sentences=5):
    try:
        import nltk
        try:
            sentences = nltk.sent_tokenize(text)
        except Exception as e:
            print(f"NLTK tokenization failed: {str(e)}")
            sentences = simple_split_sentences(text)
    except:
        print("Using simple sentence splitter as fallback")
        sentences = simple_split_sentences(text)
    
    if not sentences or len(sentences) <= num_sentences:
        if sentences:
            return ' '.join(sentences)
        return text[:1000] + "..."
    
    start = sentences[:max(1, num_sentences//2)]
    middle_idx = len(sentences)//2
    middle = sentences[middle_idx:middle_idx+1]
    end = sentences[-(num_sentences//2 + 1):]
    
    return ' '.join(start + middle + end)

def summarize_document(text: str, max_length: int = 1024) -> str:
    if not text or len(text.strip()) < 50:
        return "Document is too short or empty to summarize."
    
    try:
        text = clean_text_for_summarization(text)
        words = text.split()
        total_words = len(words)
        
        if total_words < 100:
            return text
            
        if total_words > 3000:  
            begin = ' '.join(words[:800]) 
            middle_start = max(0, (total_words // 2) - 400)
            middle = ' '.join(words[middle_start:middle_start + 800])
            end = ' '.join(words[-800:])
            
            try:
                try:
                    begin_summary = summarizer(
                        clean_text_for_summarization(begin), 
                        max_length=100, 
                        min_length=30, 
                        do_sample=False
                    )
                    begin_text = begin_summary[0]['summary_text'] if begin_summary else ""
                except:
                    begin_text = extract_key_sentences(begin, 2)
                    
                try:
                    middle_summary = summarizer(
                        clean_text_for_summarization(middle), 
                        max_length=100, 
                        min_length=30,
                        do_sample=False
                    )
                    middle_text = middle_summary[0]['summary_text'] if middle_summary else ""
                except:
                    middle_text = extract_key_sentences(middle, 2)
                    
                try:
                    end_summary = summarizer(
                        clean_text_for_summarization(end), 
                        max_length=100, 
                        min_length=30, 
                        do_sample=False
                    )
                    end_text = end_summary[0]['summary_text'] if end_summary else ""
                except:
                    end_text = extract_key_sentences(end, 2)
                
                result = f"{begin_text} {middle_text} {end_text}".strip()
                if result:
                    return result
                else:
                    return "Key points: " + extract_key_sentences(text)
                    
            except Exception as e:
                print(f"Error in sectional summarization: {str(e)}")
                return "Document overview: " + extract_key_sentences(text)
        
        elif total_words > 800:
            selected_text = ' '.join(words[:400]) + ' ' + ' '.join(words[-400:])
            
            try:
                summary = summarizer(
                    clean_text_for_summarization(selected_text),
                    max_length=150,
                    min_length=30,
                    do_sample=False
                )
                return summary[0]['summary_text']
            except Exception as e:
                print(f"Error summarizing medium doc: {str(e)}")
                return "Key points: " + extract_key_sentences(text)
            
        else:
            try:
                summary = summarizer(
                    text, 
                    max_length=min(max_length, 150), 
                    min_length=30, 
                    do_sample=False
                )
                if summary and len(summary) > 0:
                    return summary[0]['summary_text']
                else:
                    return extract_key_sentences(text, 3)
            except Exception as e:
                print(f"Direct summarization error: {str(e)}")
                return extract_key_sentences(text, 3)
    
    except Exception as e:
        print(f"Summarization error: {str(e)}")
        try:
            return "Key points: " + extract_key_sentences(text, 5)
        except Exception as inner_e:
            print(f"Even fallback extraction failed: {str(inner_e)}")
            return "Document preview: " + text[:500] + "..."

def validate_summary(summary, source_text, threshold=0.65):
    if not summary or not source_text:
        return {
            "valid": False,
            "score": 0.0,
            "message": "Missing summary or source content"
        }
    
    try:
        summary_embedding = model.encode([summary])
        
        source_chunks = chunk_text(source_text, chunk_size=500)
        chunk_embeddings = model.encode(source_chunks)
        
        similarities = np.dot(chunk_embeddings, summary_embedding.T).flatten()
        
        max_similarity = float(np.max(similarities))
        avg_similarity = float(np.mean(similarities))
        
        summary_sentences = simple_split_sentences(summary)
        
        fact_scores = []
        for sentence in summary_sentences:
            if len(sentence.split()) < 5:
                continue
                
            sentence_embedding = model.encode([sentence])
            sent_similarities = np.dot(chunk_embeddings, sentence_embedding.T).flatten()
            fact_scores.append(float(np.max(sent_similarities)))
        
        fact_validity = sum(1 for score in fact_scores if score > threshold) / max(1, len(fact_scores))
        
        is_valid = max_similarity >= threshold
        
        validation_result = {
            "valid": is_valid,
            "score": max_similarity,
            "avg_score": avg_similarity,
            "fact_validity": fact_validity,
            "message": "Summary is valid and supported by the document." if is_valid else 
                      "Summary may contain inaccuracies or unsupported information."
        }
        
        if max_similarity > 0.8:
            validation_result["confidence"] = "High"
        elif max_similarity > 0.7:
            validation_result["confidence"] = "Medium"
        else:
            validation_result["confidence"] = "Low"
            
        return validation_result
        
    except Exception as e:
        print(f"Summary validation error: {str(e)}")
        return {
            "valid": False,
            "score": 0.0,
            "message": f"Error validating summary: {str(e)}"
        }

def validate_query_summary(summary, query, chunks, embeddings, threshold=0.65):
    if not summary or not query:
        return {
            "valid": False,
            "score": 0.0,
            "message": "Missing summary or query"
        }
    
    try:
        query_embedding = model.encode([query])
        similarities = np.dot(embeddings, query_embedding.T).flatten()
        
        top_indices = np.argsort(similarities)[-3:][::-1]
        relevant_text = " ".join([chunks[i] for i in top_indices])
        
        basic_validation = validate_summary(summary, relevant_text, threshold)
        
        query_summary_embedding = model.encode([query, summary])
        query_summary_similarity = np.dot(query_summary_embedding[0], query_summary_embedding[1])
        query_relevance = float(query_summary_similarity)
        
        validation_result = basic_validation.copy()
        validation_result["query_relevance"] = query_relevance
        
        validation_result["valid"] = basic_validation["valid"] and (query_relevance > threshold)
        
        if query_relevance < threshold:
            validation_result["message"] = "Summary doesn't specifically address the query."
        elif not basic_validation["valid"]:
            validation_result["message"] = "Summary contains information not supported by the document."
        
        return validation_result
        
    except Exception as e:
        print(f"Query summary validation error: {str(e)}")
        return {
            "valid": False,
            "score": 0.0,
            "message": f"Error validating summary: {str(e)}"
        }

def detect_sections(text):
    section_patterns = [
        r'(?i)problem\s+statement\s+(\d+|[a-z])', 
        r'(?i)problem\s+statement[\s\-]*(\d+|[a-z])', 
        r'(?i)problem\s*(\d+|[a-z])\s*[:\.]+', 
        r'(?i)ps\s*[\-\.\s]*(\d+|[a-z])', 
        r'(?i)section\s+(\d+|[a-z])\s*[:\.]*', 
        r'(?i)chapter\s+(\d+|[a-z])',
        r'(?i)part\s+(\d+|[a-z])'
    ]
    
    combined_pattern = '|'.join(f'({pattern})' for pattern in section_patterns)
    
    import re
    matches = list(re.finditer(combined_pattern, text))
    
    if not matches:
        return [{"title": "Document", "start_idx": 0, "end_idx": len(text), "content": text}]
    
    sections = []
    
    for i, match in enumerate(matches):
        title = match.group(0).strip()
        
        section_num = None
        for pattern in section_patterns:
            number_match = re.search(pattern, title)
            if number_match and len(number_match.groups()) > 0:
                section_num = number_match.group(1)
                break
                
        normalized_title = title.lower()
        if 'problem statement' in normalized_title or 'ps' == normalized_title[:2]:
            std_title = f"problem statement {section_num}" if section_num else title
        else:
            std_title = title
        
        start_idx = match.start()
        
        end_idx = matches[i+1].start() if i < len(matches)-1 else len(text)
        
        content_start = match.end()
        content = text[content_start:end_idx].strip()
        
        sections.append({
            "title": title,
            "std_title": std_title,
            "section_num": section_num,
            "start_idx": start_idx,
            "end_idx": end_idx,
            "content": content
        })
    
    if len(sections) == 0:
        paragraphs = re.split(r'\n\s*\n', text)
        if len(paragraphs) > 1:
            for i, para in enumerate(paragraphs):
                if len(para.strip()) > 100:
                    sections.append({
                        "title": f"Section {i+1}",
                        "std_title": f"section {i+1}",
                        "section_num": str(i+1),
                        "start_idx": text.find(para),
                        "end_idx": text.find(para) + len(para),
                        "content": para
                    })
        else:
            sections = [{"title": "Document", "std_title": "document", "section_num": None,
                         "start_idx": 0, "end_idx": len(text), "content": text}]
    
    return sections

def extract_problem_statement_num_from_query(query):
    patterns = [
        r'(?i)problem\s+statement\s*[\-\.\s]*(\d+|[a-z])',
        r'(?i)problem\s*[\-\.\s]*(\d+|[a-z])',
        r'(?i)ps\s*[\-\.\s]*(\d+|[a-z])'
    ]
    
    import re
    for pattern in patterns:
        match = re.search(pattern, query)
        if match and match.group(1):
            return match.group(1)
    
    return None

def query_section(chunks, embeddings, metadata, prompt, target_section=None):
    if not chunks or len(chunks) == 0:
        return "No document content to search."
    
    problem_num = extract_problem_statement_num_from_query(prompt)
    
    filtered_chunks = []
    filtered_embeddings = []
    filtered_metadata = []
    section_indices = []
    
    if problem_num or target_section:
        target_problem = problem_num or target_section
        query_terms = [f"problem statement {target_problem}", 
                       f"ps{target_problem}", 
                       f"problem {target_problem}"]
        
        for i, meta in enumerate(metadata):
            section_title = meta.get("section", "").lower()
            section_num = None
            
            if "section_num" in meta:
                section_num = meta["section_num"]
            
            section_match = False
            if section_num and section_num == target_problem:
                section_match = True
            else:
                for term in query_terms:
                    if term in section_title:
                        section_match = True
                        break
            
            if section_match:
                filtered_chunks.append(chunks[i])
                filtered_embeddings.append(embeddings[i])
                filtered_metadata.append(metadata[i])
                section_indices.append(i)
        
        if not filtered_chunks:
            broader_terms = [f"statement {target_problem}", f"section {target_problem}", target_problem]
            for i, meta in enumerate(metadata):
                section_title = meta.get("section", "").lower()
                for term in broader_terms:
                    if term in section_title:
                        filtered_chunks.append(chunks[i])
                        filtered_embeddings.append(embeddings[i])
                        filtered_metadata.append(metadata[i])
                        section_indices.append(i)
                        break
    
        if not filtered_chunks:
            for i, meta in enumerate(metadata):
                print(f"Available section: {meta.get('section', 'unknown')}")
                
            return f"Could not find problem statement {target_problem} in the document."
            
        query_chunks = filtered_chunks
        query_embeddings = np.array(filtered_embeddings)
        query_metadata = filtered_metadata
        
        cleaned_prompt = re.sub(r'(?i)problem\s+statement\s*[\-\.\s]*\d+|(?i)ps\s*[\-\.\s]*\d+', '', prompt).strip()
        if cleaned_prompt:
            prompt = cleaned_prompt
    else:
        query_chunks = chunks
        query_embeddings = embeddings
        query_metadata = metadata
    
    prompt_embedding = model.encode([prompt])
    similarities = np.dot(query_embeddings, prompt_embedding.T).flatten()
    best_chunk_idx = np.argmax(similarities)
    
    context = query_chunks[best_chunk_idx]
    
    result = qa_pipeline(
        question=prompt,
        context=context,
        max_answer_len=2000
    )
    
    answer = result["answer"]
    if problem_num or target_section:
        section_info = query_metadata[best_chunk_idx].get("section", "Unknown section")
        return f"From {section_info}: {answer}"
    
    return answer

def summarize_section(sections, section_target=None, max_length=500):
    if not sections:
        return "No content to summarize."
    
    if not section_target:
        all_text = " ".join(section["content"] for section in sections)
        return summarize_document(all_text, max_length)
    
    target_lower = section_target.lower()
    matching_sections = []
    
    for section in sections:
        if target_lower in section["title"].lower():
            matching_sections.append(section)
    
    if not matching_sections:
        return f"Could not find section '{section_target}' to summarize."
    
    best_section = matching_sections[0]
    if len(matching_sections) > 1:
        for section in matching_sections:
            if section["title"].lower() == target_lower:
                best_section = section
                break
    
    return summarize_document(best_section["content"], max_length)

process_document = process_document_with_sections