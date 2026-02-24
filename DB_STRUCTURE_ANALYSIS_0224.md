# Database Structure Analysis & Recommendations

**Date**: 2026-02-24  
**Purpose**: Answer critical questions about DB scalability and implementation recommendations

---

## Question 1: Multi-Level File Organization & Future Features

### Current State: **LIMITED SUPPORT** ⚠️

#### 1.1 Current Schema
```sql
CREATE TABLE file_uploads (
    id INTEGER PRIMARY KEY,
    emp_id VARCHAR(10),
    folder_path VARCHAR(500),  -- Single-level: "2026-02-24" or "custom_folder"
    filename VARCHAR(500),
    file_size_mb FLOAT,
    uploaded_at DATETIME
);
```

**What it supports**:
- ✅ Single-level folders: `emp_id/folder_path/filename`
- ✅ Flat folder structure: `emp_id/2026-02-24/file.wav`
- ✅ Custom folder names: `emp_id/부당권유_검토/file.wav`

**What it CANNOT support**:
- ❌ Multi-level folders: `emp_id/project/phase1/file.wav`
- ❌ Nested hierarchies: `emp_id/clients/client_a/call1/file.wav`

#### 1.2 Code Evidence

**File Upload** (`web_ui/app/services/file_service.py`, Lines 52-55):
```python
# 3. 폴더 경로 생성
folder_path = file_utils.create_folder_path(emp_id, folder_name)
# Returns: "2026-02-24" or custom name (NO SLASHES ALLOWED)

# 4. 파일 저장
full_file_path = user_dir / folder_path / filename
# Structure: uploads/{emp_id}/{folder_path}/{filename}
```

**Folder Name Validation** (`web_ui/app/utils/file_utils.py`, Lines 48-53):
```python
# 위험한 문자 제거
invalid_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*', '\x00']
for char in invalid_chars:
    if char in folder_name:
        raise ValueError(f"폴더명에 사용할 수 없는 문자: {char}")
```

**CRITICAL**: Forward slashes `/` are explicitly blocked, preventing nested folders!

---

### Future Feature Requirements Analysis

#### Feature A: Move Files Between Folders

**Current Support**: ❌ **NO**

**Why it fails**:
1. No `UPDATE` operation in FileService
2. Physical file move requires filesystem operations
3. No transaction safety between DB update and file move

**What you'd need**:
```python
def move_file(emp_id: str, filename: str, 
              old_folder: str, new_folder: str, db: Session):
    """Move file between folders (DB + Filesystem)"""
    
    # 1. Update DB record
    file_record = db.query(FileUpload).filter(
        FileUpload.emp_id == emp_id,
        FileUpload.folder_path == old_folder,
        FileUpload.filename == filename
    ).first()
    
    if not file_record:
        raise FileNotFoundError("File not found in DB")
    
    # 2. Move physical file
    old_path = user_dir / old_folder / filename
    new_path = user_dir / new_folder / filename
    
    try:
        new_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old_path), str(new_path))
        
        # 3. Update DB (only after successful file move)
        file_record.folder_path = new_folder
        db.commit()
        
    except Exception as e:
        db.rollback()
        raise Exception(f"File move failed: {e}")
```

**Schema Changes Needed**: ✅ **NONE** (current schema supports this)

---

#### Feature B: Select Specific Files for Analysis

**Current Support**: ❌ **PARTIAL**

**Current Behavior** (`analysis_service.py`, Lines 85-93):
```python
# Analyzes ALL files in a folder
files = db.query(FileUpload).filter(
    FileUpload.emp_id == emp_id,
    FileUpload.folder_path == request.folder_path  # ALL files in folder!
).all()

file_list = [f.filename for f in files]
```

**What you'd need**:

1. **Add file selection to request schema**:
```python
class AnalysisStartRequest(BaseModel):
    folder_path: str
    selected_files: Optional[List[str]] = None  # NEW: specific files
    include_classification: bool = True
    include_validation: bool = False
    force_reanalysis: bool = False
```

2. **Modify query logic**:
```python
if request.selected_files:
    # Analyze only selected files
    files = db.query(FileUpload).filter(
        FileUpload.emp_id == emp_id,
        FileUpload.folder_path == request.folder_path,
        FileUpload.filename.in_(request.selected_files)  # FILTER
    ).all()
else:
    # Analyze all files (current behavior)
    files = db.query(FileUpload).filter(
        FileUpload.emp_id == emp_id,
        FileUpload.folder_path == request.folder_path
    ).all()
```

**Schema Changes Needed**: ✅ **NONE** (current schema supports this)

---

#### Feature C: Re-run Analysis on Single File

**Current Support**: ❌ **NO**

**Current Problem**: Analysis is job-based, not file-based
- Jobs process entire folders
- No way to re-analyze a single file without creating a new job
- Results are keyed by `(job_id, file_id)` - no direct file lookup

**What you'd need**:

1. **Add file-level analysis endpoint**:
```python
@router.post("/api/analysis/file")
async def analyze_single_file(
    request: Request,
    filename: str,
    folder_path: str,
    db: Session = Depends(get_db)
):
    """Analyze or re-analyze a single file"""
    emp_id = request.session.get("emp_id")
    
    # Create mini-job for one file
    job_id = f"file_{uuid.uuid4().hex[:12]}"
    
    # Process just this file
    background_tasks.add_task(
        AnalysisService.process_analysis_sync,
        job_id=job_id,
        emp_id=emp_id,
        folder_path=folder_path,
        files=[filename],  # Only one file!
        ...
    )
```

2. **Add unique constraint for latest result**:
```python
# Option A: Add version column to results table
ALTER TABLE analysis_results ADD COLUMN version INTEGER DEFAULT 1;

# Option B: Use a separate table for "active results"
CREATE TABLE latest_analysis_results (
    emp_id VARCHAR(10),
    folder_path VARCHAR(500),
    filename VARCHAR(500),
    result_id INTEGER FOREIGN KEY,  -- Points to analysis_results
    PRIMARY KEY (emp_id, folder_path, filename)
);
```

**Schema Changes Needed**: ⚠️ **YES** (need versioning or "latest result" tracking)

---

### Multi-Level Folder Support: Implementation Plan

If you want to support `emp_id/project/phase1/recording.wav`:

#### Option 1: Keep Current Schema (Recommended for now)
- Store full path in `folder_path`: `"project/phase1"`
- Remove slash validation in `file_utils.py`
- Filesystem already supports it: `Path("uploads/90001/project/phase1/file.wav")`

**Changes**:
```python
# web_ui/app/utils/file_utils.py - Line 52
# OLD:
invalid_chars = ['/', '\\', '..', ...]  # Blocks slashes

# NEW:
invalid_chars = ['..', '<', '>', ':', '"', '|', '?', '*', '\x00']  # Allow slashes
# Still block ".." for security (prevent directory traversal)
```

**Pros**: ✅ No schema changes, works immediately  
**Cons**: ⚠️ No folder hierarchy queries (can't list subfolders easily)

---

#### Option 2: Hierarchical Schema (Future-proof)

Add parent-child relationships:
```sql
CREATE TABLE folders (
    id INTEGER PRIMARY KEY,
    emp_id VARCHAR(10),
    folder_name VARCHAR(200),
    parent_folder_id INTEGER FOREIGN KEY,  -- Self-reference for tree
    full_path VARCHAR(500),  -- Computed: "project/phase1/subfolder"
    created_at DATETIME
);

CREATE TABLE file_uploads (
    id INTEGER PRIMARY KEY,
    emp_id VARCHAR(10),
    folder_id INTEGER FOREIGN KEY,  -- Link to folders table
    filename VARCHAR(500),
    file_size_mb FLOAT,
    uploaded_at DATETIME
);
```

**Pros**: ✅ True hierarchy, easy folder operations, efficient queries  
**Cons**: ⚠️ Major schema change, requires migration, more complex code

---

### Summary for Question 1

| Feature | Current Support | Schema Change Needed | Complexity |
|---------|----------------|---------------------|------------|
| **Multi-level folders** | ❌ NO (slashes blocked) | ✅ NO (just validation) | 🟢 LOW |
| **Move files between folders** | ❌ NO (no API) | ✅ NO | 🟡 MEDIUM |
| **Select specific files** | ❌ PARTIAL | ✅ NO | 🟢 LOW |
| **Re-run single file** | ❌ NO | ⚠️ YES (versioning) | 🔴 HIGH |

**Recommendation**: 
1. ✅ **Enable multi-level folders NOW** (remove slash validation)
2. ✅ **Add file selection** to analysis request
3. 🕐 **Defer move operation** until needed
4. 🕐 **Defer single-file re-run** (complex, needs versioning)

---

## Question 2: Analysis Results Lifecycle

### 2.1 How Results Are Generated

#### Step-by-Step Process

**Phase 1: Job Creation** (`analysis_service.py`, Lines 119-145)
```python
# User clicks "분석 시작"
# POST /api/analysis/start

# 1. Create job record (status = "pending")
analysis_job = AnalysisJob(
    job_id=job_id,
    emp_id=emp_id,
    folder_path=request.folder_path,
    file_ids=file_list,  # ["file1.wav", "file2.wav"]
    files_hash=current_hash,
    options=options,
    status="pending",  # ← Initial state
    started_at=datetime.utcnow()
)
db.add(analysis_job)
db.commit()
```

**Database State After Step 1**:
```sql
-- analysis_jobs table
job_id             | status   | file_ids                  | created_at
job_abc123         | pending  | ["f1.wav", "f2.wav"]      | 2026-02-24 09:00:00

-- analysis_results table
(empty - no results yet)
```

---

**Phase 2: Background Processing Starts** (`analysis_service.py`, Line 554)
```python
# Background task begins
job.status = "processing"  # ← Status update
new_db.commit()
```

**Database State After Step 2**:
```sql
-- analysis_jobs table
job_id     | status      | file_ids                  | started_at
job_abc123 | processing  | ["f1.wav", "f2.wav"]      | 2026-02-24 09:00:05

-- analysis_results table
(still empty - processing hasn't created results yet)
```

---

**Phase 3: File Processing Loop** (`analysis_service.py`, Lines 562-620)

For **EACH file**:
```python
for idx, filename in enumerate(files):
    # 3a. Track in memory (NOT in DB!)
    _current_processing[job_id] = filename  # In-memory only!
    
    # 3b. Call STT API
    stt_result = await stt_service.transcribe_local_file(file_path)
    
    # 3c. Create result record IMMEDIATELY after STT completes
    result = AnalysisResult(
        job_id=job_id,
        file_id=filename,
        stt_text=stt_result.get('text', ''),
        stt_metadata={
            "duration": stt_result.get('duration_sec', 0),
            "language": stt_result.get('language', 'ko'),
            "backend": stt_result.get('backend', 'unknown'),
            "confidence": confidence  # From STT or dummy
        },
        # ⚠️ NOTE: These fields are NULL initially!
        classification_code=None,
        classification_category=None,
        classification_confidence=None,
        improper_detection_results=None,
        incomplete_detection_results=None
    )
    
    new_db.add(result)
    new_db.commit()  # ← Committed IMMEDIATELY (per file)
```

**Database State During Processing** (file 1 done, file 2 processing):
```sql
-- analysis_jobs table
job_id     | status      | file_ids                  | completed_at
job_abc123 | processing  | ["f1.wav", "f2.wav"]      | NULL

-- analysis_results table
job_id     | file_id  | stt_text           | classification_code | created_at
job_abc123 | f1.wav   | "상담원: 안녕..."  | NULL                | 09:00:10
-- f2.wav not yet inserted

-- In-memory tracking (NOT in DB)
_current_processing = {"job_abc123": "f2.wav"}
```

---

**Phase 4: Job Completion** (`analysis_service.py`, Lines 640-648)
```python
# After ALL files processed
if job:
    job.status = "completed"  # ← Final status
    job.completed_at = datetime.utcnow()
    new_db.commit()

# Clear memory
del _current_processing[job_id]
```

**Final Database State**:
```sql
-- analysis_jobs table
job_id     | status     | file_ids                  | completed_at
job_abc123 | completed  | ["f1.wav", "f2.wav"]      | 2026-02-24 09:01:30

-- analysis_results table
job_id     | file_id  | stt_text           | classification_code | created_at
job_abc123 | f1.wav   | "상담원: 안녕..."  | NULL                | 09:00:10
job_abc123 | f2.wav   | "고객: 네..."      | NULL                | 09:01:25
```

---

### 2.2 When Do Classification Fields Get Populated?

**CRITICAL FINDING**: ⚠️ **THEY DON'T!**

Currently, these fields are **ALWAYS NULL**:
- `classification_code`
- `classification_category`
- `classification_confidence`
- `improper_detection_results`
- `incomplete_detection_results`

#### Why?

Look at the code (`analysis_service.py`, Lines 591-600):
```python
result = AnalysisResult(
    job_id=job_id,
    file_id=filename,
    stt_text=stt_result.get('text', ''),
    stt_metadata={...},
    # ⚠️ Classification fields are NOT set!
)
```

**The STT API response structure** (`stt_service.py`, Lines 495-510):
```python
return {
    "success": True,
    "text": dummy_text,
    "duration_sec": 60,
    "backend": "dummy",
    "language": language,
    "processing_steps": {
        "stt": True,
        "privacy_removal": False,
        "classification": False,  # ← Always False in dummy mode
        "ai_agent": False
    },
    # ⚠️ NO classification data in response!
}
```

**What SHOULD happen** (when real AI agent is integrated):

```python
# Real API response (future)
{
    "success": True,
    "text": "상담원: 안녕하세요...",
    "classification": {  # NEW section
        "code": "200-100",
        "category": "위험",
        "confidence": 0.85
    },
    "improper_detection": {  # NEW section
        "detected": True,
        "score": 0.78,
        "segments": [
            {"start": 10, "end": 15, "text": "원금 보장됩니다", "confidence": 0.9}
        ]
    },
    "incomplete_detection": {  # NEW section
        "detected": False,
        "score": 0.12
    }
}

# Then populate DB:
result = AnalysisResult(
    job_id=job_id,
    file_id=filename,
    stt_text=stt_result['text'],
    classification_code=stt_result['classification']['code'],
    classification_category=stt_result['classification']['category'],
    classification_confidence=stt_result['classification']['confidence'],
    improper_detection_results=stt_result['improper_detection'],
    incomplete_detection_results=stt_result['incomplete_detection']
)
```

---

### 2.3 How Web UI Gets Real-Time Updates

**Polling Mechanism** (`templates/analysis.html`, Lines ~820-850):

```javascript
// Start polling every 2 seconds
const pollInterval = setInterval(async () => {
    const response = await fetch(`/api/analysis/progress/${jobId}`);
    const data = await response.json();
    
    // Update progress bar
    document.getElementById('progressBar').style.width = data.progress + '%';
    
    // Update results table
    updateResultsTable(data.results);
    
    // Stop polling when complete
    if (data.status === 'completed') {
        clearInterval(pollInterval);
    }
}, 2000);  // Every 2 seconds
```

**Backend Progress Endpoint** (`analysis_service.py`, Lines 181-260):

```python
@staticmethod
def get_progress(job_id: str, emp_id: str, db: Session):
    # 1. Get job from DB
    job = db.query(AnalysisJob).filter(
        AnalysisJob.job_id == job_id
    ).first()
    
    # 2. Get completed results from DB
    results = db.query(AnalysisResult).filter(
        AnalysisResult.job_id == job_id
    ).all()
    
    processed_files = len(results)
    
    # 3. Get current processing file from MEMORY (not DB!)
    current_processing_file = _current_processing.get(job_id)
    
    # 4. Build status for EACH file
    for filename in job.file_ids:
        result = results_dict.get(filename)
        
        if result:
            # File completed - read from DB
            file_status = "completed"
            confidence = result.stt_metadata.get("confidence", 0.5)
            risk_level = calculate_risk(confidence)
        elif filename == current_processing_file:
            # File being processed - from memory
            file_status = "processing"
        else:
            # File not started yet
            file_status = "pending"
        
        results_list.append({
            "filename": filename,
            "stt_text": result.stt_text if result else None,
            "status": file_status,
            "confidence": confidence,
            "risk_level": risk_level
        })
    
    return AnalysisProgressResponse(
        job_id=job_id,
        status=job.status,
        progress=progress,
        current_file=current_processing_file,
        results=results_list  # ← This gets sent to browser
    )
```

**Key Insight**: 
- ✅ Completed files: Status from **database** (`analysis_results` table)
- ⚠️ Current file: Status from **in-memory dictionary** (`_current_processing`)
- ❌ Pending files: Status **computed** (not stored anywhere)

---

### Summary for Question 2

**How DB entries change during processing**:

| Time | Job Status | Results Table | Memory |
|------|-----------|---------------|--------|
| T0: Request received | `pending` | Empty | - |
| T1: Processing starts | `processing` | Empty | - |
| T2: File 1 processing | `processing` | Empty | `{"job_abc": "f1.wav"}` |
| T3: File 1 done | `processing` | 1 row (f1.wav) | `{"job_abc": "f1.wav"}` |
| T4: File 2 processing | `processing` | 1 row | `{"job_abc": "f2.wav"}` |
| T5: File 2 done | `processing` | 2 rows | `{"job_abc": "f2.wav"}` |
| T6: All done | `completed` | 2 rows | (cleared) |

**When fields are populated**:
- ✅ **Immediately**: `stt_text`, `stt_metadata`, `file_id`, `job_id`
- ⚠️ **Never (currently)**: `classification_*`, `improper_detection_*`, `incomplete_detection_*`
- 🔮 **Future**: When real AI agent returns classification data

**Web communication**:
- Frontend polls `/api/analysis/progress/{job_id}` every 2 seconds
- Backend queries DB + memory, returns JSON
- No WebSocket, no push notifications (pull-based only)

---

## Question 3: Implementing Recommendations 2 & 4

### Recommendation 2: Add Status Column to `analysis_results`

#### Current Problem
```python
# Memory-based tracking (lost on restart!)
_current_processing: Dict[str, str] = {"job_abc": "file.wav"}
```

**If server restarts during processing**:
- ❌ All "processing" status is lost
- ❌ Cannot resume interrupted jobs
- ❌ UI shows wrong status

#### Proposed Solution

**Add status column**:
```sql
ALTER TABLE analysis_results ADD COLUMN status VARCHAR(20) DEFAULT 'pending';
-- Values: 'pending' | 'processing' | 'completed' | 'failed'
```

---

### Implementation Plan for Recommendation 2

#### Step 1: Database Migration

**Create migration script** (`web_ui/migrations/add_result_status.py`):
```python
from app.utils.db import SessionLocal, engine
from sqlalchemy import text

def upgrade():
    """Add status column to analysis_results"""
    with engine.connect() as conn:
        # Add column with default
        conn.execute(text("""
            ALTER TABLE analysis_results 
            ADD COLUMN status VARCHAR(20) DEFAULT 'completed'
        """))
        
        # Update existing rows (assume they're all completed)
        conn.execute(text("""
            UPDATE analysis_results 
            SET status = 'completed' 
            WHERE status IS NULL
        """))
        
        conn.commit()
        print("✅ Added status column to analysis_results")

if __name__ == "__main__":
    upgrade()
```

**Run migration**:
```bash
cd /Users/a114302/Desktop/Github/stt_engine/web_ui
./venv/bin/python migrations/add_result_status.py
```

---

#### Step 2: Update ORM Model

**File**: `web_ui/app/models/database.py` (Line ~120)

**BEFORE**:
```python
class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String(50), ForeignKey("analysis_jobs.job_id"))
    file_id = Column(String(500), nullable=False)
    stt_text = Column(Text)
    stt_metadata = Column(JSON)
    # ... other fields
    created_at = Column(DateTime, default=datetime.utcnow)
```

**AFTER**:
```python
class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String(50), ForeignKey("analysis_jobs.job_id"))
    file_id = Column(String(500), nullable=False)
    
    # NEW: Status tracking
    status = Column(String(20), default='pending')  # ← ADD THIS
    # Values: 'pending' | 'processing' | 'completed' | 'failed'
    
    stt_text = Column(Text)
    stt_metadata = Column(JSON)
    # ... other fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)  # ← ADD THIS TOO
```

---

#### Step 3: Update Analysis Processing Logic

**File**: `web_ui/app/services/analysis_service.py`

**Changes needed in multiple places**:

**3a. Create pending results upfront** (Lines ~560):

**BEFORE**:
```python
for idx, filename in enumerate(files):
    # Track in memory
    _current_processing[job_id] = filename
    
    # Process file
    stt_result = await stt_service.transcribe_local_file(...)
    
    # Save result after processing
    result = AnalysisResult(...)
    new_db.add(result)
    new_db.commit()
```

**AFTER**:
```python
# Create ALL result records upfront with status='pending'
for filename in files:
    pending_result = AnalysisResult(
        job_id=job_id,
        file_id=filename,
        status='pending',  # ← NEW
        stt_text=None,
        stt_metadata=None
    )
    new_db.add(pending_result)
new_db.commit()

# Then process each file
for idx, filename in enumerate(files):
    # Update status to 'processing'
    result = new_db.query(AnalysisResult).filter(
        AnalysisResult.job_id == job_id,
        AnalysisResult.file_id == filename
    ).first()
    
    result.status = 'processing'  # ← NEW
    new_db.commit()
    
    # Process file
    stt_result = await stt_service.transcribe_local_file(...)
    
    # Update with results
    result.stt_text = stt_result.get('text')
    result.stt_metadata = {...}
    result.status = 'completed'  # ← NEW
    result.updated_at = datetime.utcnow()
    new_db.commit()
```

**3b. Remove in-memory tracking** (Lines ~260, ~565, ~640):

**DELETE THESE**:
```python
# DELETE from class definition
_current_processing: Dict[str, str] = {}

# DELETE from processing loop
_current_processing[job_id] = filename

# DELETE from cleanup
del _current_processing[job_id]
```

**3c. Update progress query** (Lines ~230):

**BEFORE**:
```python
# Get current processing file from memory
current_processing_file = _current_processing.get(job_id)

# Determine status per file
for filename in job.file_ids:
    result = results_dict.get(filename)
    
    if result:
        file_status = "completed"
    elif filename == current_processing_file:
        file_status = "processing"
    else:
        file_status = "pending"
```

**AFTER**:
```python
# Query ALL results including pending ones
results = new_db.query(AnalysisResult).filter(
    AnalysisResult.job_id == job_id
).all()

# Status comes directly from DB!
for result in results:
    result_dict = {
        "filename": result.file_id,
        "stt_text": result.stt_text,
        "status": result.status,  # ← FROM DB!
        "confidence": result.stt_metadata.get("confidence", 0) if result.stt_metadata else 0,
        "risk_level": calculate_risk(confidence)
    }
    results_list.append(result_dict)
```

---

### Recommendation 4: Use `analysis_progress` Table

#### Current Problem

The `analysis_progress` table exists but is **NEVER USED**:
```sql
CREATE TABLE analysis_progress (
    id INTEGER PRIMARY KEY,
    job_id VARCHAR(50),
    file_id VARCHAR(500),
    progress_percent INTEGER,
    status VARCHAR(20),
    message TEXT,
    updated_at DATETIME
);

-- Query result:
SELECT * FROM analysis_progress;
-- (0 rows)  ← EMPTY!
```

Progress is calculated **on-the-fly** every time frontend polls.

#### Proposed Solution

**Use this table to persist progress snapshots**:
- One row per file per job
- Updated as files are processed
- Can show historical progress (not just current)

---

### Implementation Plan for Recommendation 4

#### Step 1: Update Analysis Processing

**File**: `web_ui/app/services/analysis_service.py` (Lines ~562-620)

**ADD progress tracking**:

```python
for idx, filename in enumerate(files):
    try:
        # Calculate progress
        progress_percent = int((idx / total_files) * 100)
        
        # Update progress table
        progress_record = new_db.query(AnalysisProgress).filter(
            AnalysisProgress.job_id == job_id,
            AnalysisProgress.file_id == filename
        ).first()
        
        if not progress_record:
            progress_record = AnalysisProgress(
                job_id=job_id,
                file_id=filename
            )
            new_db.add(progress_record)
        
        # Update: File processing started
        progress_record.progress_percent = progress_percent
        progress_record.status = 'processing'
        progress_record.message = f'처리 중: {filename}'
        progress_record.updated_at = datetime.utcnow()
        new_db.commit()
        
        # Process file
        stt_result = await stt_service.transcribe_local_file(...)
        
        # Update: File completed
        progress_record.status = 'completed'
        progress_record.progress_percent = int(((idx + 1) / total_files) * 100)
        progress_record.message = f'완료: {filename}'
        progress_record.updated_at = datetime.utcnow()
        new_db.commit()
        
    except Exception as e:
        # Update: File failed
        progress_record.status = 'failed'
        progress_record.message = f'실패: {str(e)}'
        progress_record.updated_at = datetime.utcnow()
        new_db.commit()
```

---

#### Step 2: Update Progress Query

**File**: `web_ui/app/services/analysis_service.py` (Lines ~180-260)

**OPTION A: Use progress table as primary source**:
```python
def get_progress(job_id: str, emp_id: str, db: Session):
    # Get job
    job = db.query(AnalysisJob).filter(...).first()
    
    # Query progress table (instead of calculating)
    progress_records = db.query(AnalysisProgress).filter(
        AnalysisProgress.job_id == job_id
    ).all()
    
    # Build response from progress records
    results_list = []
    for prog in progress_records:
        # Get full result data
        result = db.query(AnalysisResult).filter(
            AnalysisResult.job_id == job_id,
            AnalysisResult.file_id == prog.file_id
        ).first()
        
        results_list.append({
            "filename": prog.file_id,
            "status": prog.status,  # From progress table
            "message": prog.message,  # From progress table
            "stt_text": result.stt_text if result else None,
            "confidence": result.stt_metadata.get("confidence") if result else 0
        })
    
    # Overall progress from progress table
    completed_count = sum(1 for p in progress_records if p.status == 'completed')
    progress = int((completed_count / len(progress_records)) * 100)
    
    return AnalysisProgressResponse(
        job_id=job_id,
        status=job.status,
        progress=progress,
        results=results_list
    )
```

---

### Impact Analysis: What Could Break?

#### 🔴 **HIGH RISK Areas**

1. **Existing Analysis Jobs in Database**
   - Issue: Old results don't have `status` column
   - Solution: Migration sets default `'completed'` for existing rows
   - Test: Query old jobs to ensure they still display

2. **Frontend Polling Logic** (`templates/analysis.html`)
   - Issue: May expect specific field names/structure
   - Must verify: `result.status` field exists and has correct values
   - Test: Load analysis page with in-progress job

3. **CSV Export** (Lines ~840-870 in analysis.html)
   - Currently exports: `filename`, `stt_text`, `risk_level`
   - May need to add: `status` column
   - Test: Export results, check CSV format

#### 🟡 **MEDIUM RISK Areas**

4. **Error Handling in Background Task**
   - Currently: If file fails, no result row created
   - After change: Must create result with `status='failed'`
   - Test: Process invalid audio file, verify error status

5. **Job Status Transitions**
   - Currently: `pending` → `processing` → `completed`
   - Must ensure: File statuses align with job status
   - Test: Check all files are `'completed'` when job is `'completed'`

6. **Progress Calculation**
   - Currently: `processed_files / total_files`
   - After: Must count DB rows with `status='completed'`
   - Test: Verify progress bar shows correct percentage

#### 🟢 **LOW RISK Areas**

7. **STT Service** (`stt_service.py`)
   - No changes needed - just returns JSON
   - Test: Verify dummy responses still work

8. **File Upload** (`file_service.py`)
   - Not affected by analysis changes
   - Test: Upload file, verify it appears in folder list

9. **Login/Auth** (`auth.py`)
   - Completely independent
   - No testing needed

---

### Recommended Testing Checklist

After implementing Recommendations 2 & 4:

```bash
# 1. Database Migration
cd /Users/a114302/Desktop/Github/stt_engine/web_ui
./venv/bin/python migrations/add_result_status.py
sqlite3 data/stt_web.db "PRAGMA table_info(analysis_results);" | grep status
# Should show: status|VARCHAR(20)|0||'pending'|0

# 2. Check Existing Data
sqlite3 data/stt_web.db "SELECT job_id, file_id, status FROM analysis_results LIMIT 5;"
# All old rows should show status='completed'

# 3. Start Servers
./start_api_server.sh &
cd web_ui && ./venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8100 --reload &

# 4. Manual UI Test
# - Login with employee 10001
# - Upload 3 audio files
# - Start analysis
# - Watch progress update (should show: pending → processing → completed)
# - Check browser console for errors
# - Export CSV and verify format

# 5. Database Verification During Processing
# Open another terminal while analysis is running:
sqlite3 data/stt_web.db "SELECT file_id, status, updated_at FROM analysis_results WHERE job_id = 'job_xxx' ORDER BY updated_at;"
# Should see statuses changing in real-time

# 6. Check Progress Table
sqlite3 data/stt_web.db "SELECT * FROM analysis_progress WHERE job_id = 'job_xxx';"
# Should see one row per file with progress updates

# 7. Error Handling Test
# Upload invalid file (e.g., .txt renamed to .wav)
# Start analysis
# Verify:
#   - Result row created with status='failed'
#   - Job completes despite error
#   - Error message shown in UI

# 8. Restart Resilience Test
# Start analysis
# While processing, kill server: pkill -f "uvicorn"
# Restart server
# Re-open analysis page
# Verify: Status persists (no "processing" files after restart)
```

---

### Migration Rollback Plan

If something breaks:

```python
# rollback_status_column.py
from app.utils.db import engine
from sqlalchemy import text

def downgrade():
    """Remove status column"""
    with engine.connect() as conn:
        # SQLite doesn't support DROP COLUMN directly
        # Must recreate table without column
        
        # 1. Create backup
        conn.execute(text("""
            CREATE TABLE analysis_results_backup AS 
            SELECT * FROM analysis_results
        """))
        
        # 2. Drop original
        conn.execute(text("DROP TABLE analysis_results"))
        
        # 3. Recreate without status column
        conn.execute(text("""
            CREATE TABLE analysis_results (
                id INTEGER PRIMARY KEY,
                job_id VARCHAR(50),
                file_id VARCHAR(500),
                stt_text TEXT,
                stt_metadata JSON,
                -- ... other columns (excluding status)
                created_at DATETIME
            )
        """))
        
        # 4. Copy data back (excluding status)
        conn.execute(text("""
            INSERT INTO analysis_results 
            SELECT id, job_id, file_id, stt_text, stt_metadata, ... 
            FROM analysis_results_backup
        """))
        
        # 5. Drop backup
        conn.execute(text("DROP TABLE analysis_results_backup"))
        
        conn.commit()
        print("✅ Rolled back status column")
```

---

## Summary & Recommendations

### Question 1: Multi-Level Files
- ✅ **Do NOW**: Remove slash validation to enable nested folders
- ✅ **Do NEXT**: Add file selection to analysis request
- 🕐 **Later**: Implement file move operation
- 🕐 **Later**: Add single-file re-run (needs versioning)

### Question 2: Results Lifecycle
- Results created **immediately** after each file's STT completes
- Status tracked in **memory only** (lost on restart) ⚠️
- Classification fields are **always NULL** (waiting for real AI agent)
- Web polls **every 2 seconds** to get updates

### Question 3: Implementation Impact
- **Recommendation 2** (status column):
  - Risk Level: 🟡 MEDIUM
  - Schema Change: ✅ Required (migration needed)
  - Code Changes: 5-6 files
  - Benefits: Persistent status, restart resilience
  
- **Recommendation 4** (use progress table):
  - Risk Level: 🟢 LOW
  - Schema Change: ✅ Not required (table exists)
  - Code Changes: 2-3 files
  - Benefits: Historical tracking, better debugging

**Recommended Order**:
1. ✅ Test current system thoroughly (establish baseline)
2. ✅ Implement Recommendation 2 (status column) first
3. ✅ Test extensively after Recommendation 2
4. ✅ Implement Recommendation 4 (progress table) second
5. ✅ Final integration testing

---

**Ready to proceed with implementation?** 🚀
