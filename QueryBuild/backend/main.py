from fastapi import FastAPI, Form, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .generate_notebook import generate_notebook
from .generate_ppt import generate_ppt
from .generate_code import generate_code_file
import zipfile
import os
import uuid
import traceback

app = FastAPI()

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Track job status
job_status = {}

# Add a simple status endpoint for connectivity testing
@app.get("/status/{job_id}")
def check_status(job_id: str):
    if job_id == "test":
        # Just a connectivity test
        return {"status": "ok", "message": "Server is reachable"}
    
    if job_id not in job_status:
        return JSONResponse(status_code=404, content={"error": "Job not found"})
    
    return job_status[job_id]

@app.post("/generate/")
def generate_files(
    background_tasks: BackgroundTasks, 
    problem_statement: str = Form(...), 
    language: str = Form(None),
    output_types: str = Form("code")  # Default to code only, can be "code,notebook,ppt" or any combination
):
    try:
        # Log incoming request details
        print(f"Received generation request: language={language}, types={output_types}")
        print(f"Problem statement length: {len(problem_statement)}")
        
        # Generate a unique job ID
        job_id = str(uuid.uuid4())
        job_status[job_id] = {"status": "processing", "progress": 0}
        
        # Start the background task
        background_tasks.add_task(
            process_generation, 
            problem_statement=problem_statement,
            job_id=job_id,
            language=language,
            output_types=output_types
        )
        
        print(f"Job {job_id} created and started processing")
        return {"job_id": job_id, "status": "processing"}
    except Exception as e:
        print(f"Error in generation endpoint: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

def process_generation(problem_statement: str, job_id: str, language: str = None, output_types: str = "code"):
    try:
        output_dir = f"output/generated_files/{job_id}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Parse requested output types
        requested_types = [t.strip().lower() for t in output_types.split(",")]
        generated_files = []
        progress_step = 90 / max(len(requested_types), 1)  # Distribute progress across requested types
        current_progress = 0
        
        # Generate code if requested
        if "code" in requested_types or (language and language.lower() != "notebook"):
            lang_to_use = language or None  # Pass None to let generate_code_file detect the language from the query
            job_status[job_id]["progress"] = current_progress + progress_step/2
            job_status[job_id]["status"] = f"analyzing query and generating code"
            print(f"Job {job_id}: Analyzing query and generating appropriate code")
            
            # Generate code and let the function determine the proper file type
            code_path = generate_code_file(problem_statement, lang_to_use, f"{output_dir}/solution")
            generated_files.append((code_path, os.path.basename(code_path)))
            current_progress += progress_step
            
            # Update status with detected language
            detected_lang = os.path.splitext(os.path.basename(code_path))[1][1:]  # Get extension without dot
            job_status[job_id]["status"] = f"generated {detected_lang} code"
        
        # Generate notebook if requested
        if "notebook" in requested_types or (language and language.lower() == "notebook"):
            job_status[job_id]["progress"] = current_progress + progress_step/2
            job_status[job_id]["status"] = "generating notebook"
            print(f"Job {job_id}: Starting notebook generation")
            
            notebook_path = generate_notebook(problem_statement, f"{output_dir}/notebook.ipynb")
            generated_files.append((notebook_path, "notebook.ipynb"))
            current_progress += progress_step
        
        # Generate PowerPoint if requested
        if "ppt" in requested_types or "presentation" in requested_types:
            job_status[job_id]["progress"] = current_progress + progress_step/2
            job_status[job_id]["status"] = "generating presentation"
            print(f"Job {job_id}: Starting presentation generation")
            
            ppt_path = generate_ppt(problem_statement, f"{output_dir}/presentation.pptx")
            generated_files.append((ppt_path, "presentation.pptx"))
            current_progress += progress_step
        
        # Create zip file if files were generated
        if generated_files:
            # Update status - starting zip creation
            job_status[job_id]["progress"] = 80
            job_status[job_id]["status"] = "packaging files"
            print(f"Job {job_id}: Starting file packaging")
            
            zip_path = f"{output_dir}/project_package.zip"
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for file_path, arcname in generated_files:
                    zipf.write(file_path, arcname=arcname)
            
            # Final status update
            job_status[job_id].update({
                "status": "completed", 
                "progress": 100, 
                "file_path": zip_path
            })
            print(f"Job {job_id} completed successfully. Status: {job_status[job_id]}")
        else:
            job_status[job_id].update({
                "status": "failed", 
                "error": "No output types were specified or recognized",
                "progress": 0
            })
            
    except Exception as e:
        print(f"Error processing job {job_id}: {str(e)}")
        job_status[job_id].update({
            "status": "failed", 
            "error": str(e),
            "progress": 0
        })

@app.get("/download/{job_id}")
def download_file(job_id: str):
    if job_id not in job_status or job_status[job_id]["status"] != "completed":
        return JSONResponse(status_code=404, content={"error": "Files not ready or job not found"})
    
    return FileResponse(
        job_status[job_id]["file_path"], 
        media_type='application/zip', 
        filename="project_package.zip"
    )